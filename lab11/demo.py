"""Датчик, таблица, мониторинг и аукцион варианта 3."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .rx_mini import operators as op
from .rx_mini.cells import Cell
from .rx_mini.core import Observable, of
from .rx_mini.subjects import Subject
from .rx_mini.testing import VirtualScheduler, materialize, timer


class EventSource:
    """Классическая рассылка событий без терминального канала."""

    def __init__(self) -> None:
        self.handlers: dict[object, Callable] = {}

    def subscribe(self, handler: Callable) -> Callable:
        """Подписать обработчик и вернуть функцию отписки."""
        token = object()
        self.handlers[token] = handler

        def unsubscribe() -> None:
            self.handlers.pop(token, None)

        return unsubscribe

    def emit(self, value: Any) -> None:
        """Разослать значение обработчикам."""
        for handler in tuple(self.handlers.values()):
            handler(value)


def monitor(
    cpu: Observable,
    memory: Observable,
    requests: Observable,
) -> tuple[Observable, Observable]:
    """Собрать оповещения и полные скользящие окна из пяти измерений."""
    alerts = op.combine_latest(cpu, memory).pipe(
        op.map_(lambda p: p[0] > 90 and p[1] > 80),
        op.distinct_until_changed(),
        op.filter_(bool),
    )
    averages = requests.pipe(
        op.scan(lambda window, n: (*window[-4:], n), ()),
        op.filter_(lambda window: len(window) == 5),
        op.map_(lambda window: sum(window) / len(window)),
    )
    return alerts, averages


@dataclass(frozen=True)
class Bid:
    """Ставка участника."""

    bidder: str
    amount: int


@dataclass(frozen=True)
class Auction:
    """Публичное состояние аукциона."""

    leader: Bid | None = None
    closed: bool = False


def next_auction(state: Auction, event: Bid | None) -> Auction:
    """Принять повышение или закрыть аукцион по таймауту."""
    if state.closed:
        return state
    if event is None:
        return Auction(state.leader, True)
    if state.leader is None or event.amount > state.leader.amount:
        return Auction(event)
    return state


def auction(bids: Observable, clock: VirtualScheduler, duration: int) -> Observable:
    """Публиковать лидера до фиксированного дедлайна от подписки."""
    valid = bids.pipe(op.filter_(lambda b: b.amount > 0 and bool(b.bidder.strip())))
    deadline = timer(duration, clock).pipe(op.map_(lambda _: None))
    return (
        op.merge(deadline, valid)
        .pipe(
            op.scan(next_auction, Auction()),
            op.start_with(Auction()),
            op.distinct_until_changed(),
        )
        .pipe(
            # Открытые состояния и одно финальное уведомление.
            op.map_(lambda state: of(state) if not state.closed else of(state, None)),
            op.flat_map(op.identity),
            op.take_while(lambda state: state is not None),
        )
    )


def server_inputs() -> tuple[tuple[str, int], ...]:
    """Вернуть одну и ту же последовательность для двух реализаций."""
    return (
        ("cpu", 80),
        ("memory", 70),
        ("cpu", 95),
        ("memory", 83),
        ("cpu", 97),
        ("memory", 80),
        ("memory", 85),
        *(("requests", v) for v in (10, 20, 30, 40, 50, 60, 70)),
    )


def main() -> None:
    """Запустить демонстрации всех практических сценариев."""
    sensor = EventSource()
    readings, warnings, statistics = [], [], []
    sensor.subscribe(readings.append)
    sensor.subscribe(lambda n: warnings.append(n) if n >= 30 else None)
    sensor.subscribe(lambda n: statistics.append((sum(readings) / len(readings), max(readings))))
    for reading in (20, 34, 26):
        sensor.emit(reading)
    print("1. Датчик:", readings, warnings, statistics)

    for name, stream in (
        ("map", of(1, 2).pipe(op.map_(lambda x: x * 2))),
        ("distinct", of(1, 1, 2, 2, 3).pipe(op.distinct_until_changed())),
        ("zip", op.zip_(of(1, 2), of("a", "b"))),
    ):
        print("2–3.", name, materialize(stream))

    price, qty, discount = Cell(100), Cell(2), Cell(0.1)
    net = Cell.formula(lambda p, q, d: p * q * (1 - d), price, qty, discount)
    tax = Cell.formula(lambda n: round(n * 0.12, 2), net)
    total = Cell.formula(lambda n, t: round(n + t, 2), net, tax)
    changes = []
    total.subscribe(changes.append)
    qty.set(3)
    assert changes == [302.4]
    print("4. Таблица:", net.value, tax.value, total.value, "уведомления", changes)

    sources = {name: Subject() for name in ("cpu", "memory", "requests")}
    alerts, averages = monitor(**sources)
    alert_log, average_log = materialize(alerts), materialize(averages)
    for name, value in server_inputs():
        sources[name].on_next(value)
    for source in sources.values():
        source.on_completed()
    print("5. Мониторинг:", alert_log, average_log)

    clock, bids = VirtualScheduler(), Subject()
    states = []
    auction(bids, clock, 30).subscribe(lambda state: states.append((clock.now, state)))
    for time, bid in (
        (5, Bid("Алия", 100)),
        (9, Bid("Нур", 90)),
        (17, Bid("Нур", 150)),
        (32, Bid("Алия", 170)),
    ):
        clock.schedule(time, lambda b=bid: bids.on_next(b))
    clock.advance_to(40)
    assert [time for time, _ in states] == [0, 5, 17, 30]
    print("6. Аукцион:", states)


if __name__ == "__main__":
    main()
