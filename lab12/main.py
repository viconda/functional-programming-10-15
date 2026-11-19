"""Композиция потоков RxPY, виртуальное время и парковка."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any

import reactivex as rx
from reactivex import Observable
from reactivex import operators as op
from reactivex.abc import SchedulerBase
from reactivex.scheduler.eventloop import AsyncIOScheduler
from reactivex.scheduler.mainloop import TkinterScheduler
from reactivex.subject import Subject

from lab11.demo import server_inputs


def monitor(
    cpu: Observable,
    memory: Observable,
    requests: Observable,
) -> tuple[Observable, Observable]:
    """Собрать те же оповещения и скользящие средние, что и в работе 11."""
    alerts = rx.combine_latest(cpu, memory).pipe(
        op.map(lambda p: p[0] > 90 and p[1] > 80),
        op.distinct_until_changed(),
        op.filter(bool),
    )
    averages = requests.pipe(
        op.buffer_with_count(5, 1),
        op.filter(lambda window: len(window) == 5),
        op.map(lambda window: sum(window) / 5),
    )
    return alerts, averages


def basket(prices: Observable, quantities: Observable) -> Observable:
    """Пересчитать сумму при изменении цены или количества."""
    return rx.combine_latest(prices, quantities).pipe(
        op.map(lambda pair: sum(pair[0][sku] * n for sku, n in pair[1].items()))
    )


def convert(buys: Observable, rates: Observable) -> Observable:
    """Применить последний курс только в момент покупки."""
    return buys.pipe(op.with_latest_from(rates), op.map(lambda p: round(p[0] * p[1], 2)))


def headlines(*feeds: Observable) -> Observable:
    """Объединить новости и убрать повторы по заголовку."""
    return rx.merge(*feeds).pipe(op.distinct(lambda title: title.casefold().strip()))


def city_totals(orders: Observable) -> Observable:
    """Накопить отдельную сумму по каждому городу."""
    return orders.pipe(
        op.group_by(lambda order: order[0]),
        op.flat_map(
            lambda group: group.pipe(
                op.scan(lambda total, order: total + order[1], 0),
                op.map(lambda total: (group.key, total)),
            )
        ),
    )


def search(typing: Observable, scheduler: SchedulerBase) -> Observable:
    """Нормализовать ввод и переключаться на последний допущенный запрос."""
    catalog = ("алматы", "алдан", "алушта", "астана", "астрахань")
    return typing.pipe(
        op.map(lambda text: text.strip().casefold()),
        op.debounce(50, scheduler=scheduler),
        op.filter(lambda text: len(text) >= 3),
        op.distinct_until_changed(),
        op.map(
            lambda prefix: rx.timer(90, scheduler=scheduler).pipe(
                op.map(lambda _: tuple(city for city in catalog if city.startswith(prefix)))
            )
        ),
        op.switch_latest(),
    )


@dataclass(frozen=True)
class Result:
    """Обработанная запись или описание ошибки в записи."""

    value: int | None = None
    error: str | None = None


def parse(raw: str) -> Result:
    """Преобразовать ошибку конкретной записи в значение."""
    try:
        return Result(int(raw))
    except ValueError:
        return Result(error=f"Ожидалось целое: {raw}")


def resilient(seed: int) -> tuple[Observable, list[float]]:
    """Создать холодный случайный источник, retry и резерв с журналом попыток."""
    draws: list[float] = []

    def build(_: SchedulerBase) -> Observable:
        rng = random.Random(seed)
        draws.clear()

        def attempt(_: SchedulerBase) -> Observable:
            draw = rng.random()
            draws.append(draw)
            return rx.throw(RuntimeError("Сбой источника")) if draw < 0.3 else rx.of("основной")

        return rx.defer(attempt).pipe(op.retry(3), op.catch(rx.of("резервный")))

    return rx.defer(build), draws


async def fetch(source: str, tick: int) -> tuple[str, int]:
    """Имитировать ответ независимого источника."""
    shifts = {"A": 10, "B": 20, "C": 30}
    await asyncio.sleep(shifts[source] / 1000)
    return source, shifts[source] + tick


async def loader(duration: float) -> list[tuple[int, float]]:
    """Периодически запускать три запроса и останавливать их по дедлайну."""
    if duration <= 0:
        return []
    loop = asyncio.get_running_loop()
    scheduler = AsyncIOScheduler(loop)
    active: set[asyncio.Task] = set()
    summaries: list[tuple[int, float]] = []
    done = asyncio.Event()
    errors: list[Exception] = []

    def request(source: str, tick: int) -> Observable:
        task = asyncio.create_task(fetch(source, tick))
        active.add(task)
        task.add_done_callback(active.discard)
        return rx.from_future(task)

    def remember(error: Exception) -> None:
        errors.append(error)
        done.set()

    stream = rx.interval(0.2, scheduler=scheduler).pipe(
        op.flat_map(
            lambda tick: rx.fork_join(*(request(source, tick) for source in ("A", "B", "C")))
        ),
        op.map(lambda batch: sum(value for _, value in batch) / len(batch)),
        op.scan(lambda state, avg: (state[0] + 1, (*state[1][-2:], avg)), (0, ())),
        op.map(lambda state: (state[0], sum(state[1]) / len(state[1]))),
        op.take_until(rx.timer(duration, scheduler=scheduler)),
    )
    subscription = stream.subscribe(summaries.append, remember, done.set, scheduler=scheduler)
    try:
        await done.wait()
    finally:
        subscription.dispose()
        pending = tuple(active)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    if errors:
        raise errors[0]
    return summaries


@dataclass(frozen=True)
class Event:
    """Входное событие парковки."""

    kind: str
    spot: str
    occupied: bool = False


@dataclass(frozen=True)
class Board:
    """Неизменяемые множества занятых и забронированных мест."""

    occupied: frozenset[str] = frozenset()
    reserved: frozenset[str] = frozenset()


def apply_event(board: Board, event: Event) -> Board:
    """Применить датчик, бронь или отмену с соблюдением инварианта."""
    spot = {event.spot}
    if event.kind == "sensor":
        if event.occupied:
            return Board(board.occupied | spot, board.reserved - spot)
        return Board(board.occupied - spot, board.reserved)
    if event.kind == "reserve" and event.spot not in board.occupied:
        return Board(board.occupied, board.reserved | spot)
    if event.kind == "cancel":
        return Board(board.occupied, board.reserved - spot)
    return board


def pipeline(
    sensors: Observable,
    reservations: Observable,
    scheduler: SchedulerBase,
    spots: tuple[str, ...] = ("A1", "A2", "A3"),
    update_delay: float = 0.05,
) -> Observable:
    """Обновлять табло, коалесцируя быстрые последовательные изменения."""
    return rx.merge(
        sensors.pipe(op.filter(lambda e: e.kind == "sensor")),
        reservations.pipe(op.filter(lambda e: e.kind in ("reserve", "cancel"))),
    ).pipe(
        op.filter(lambda event: event.spot in spots),
        op.scan(apply_event, Board()),
        op.start_with(Board()),
        op.distinct_until_changed(),
        op.map(
            lambda b: (
                tuple(sorted(set(spots) - b.occupied - b.reserved)),
                tuple(sorted(b.reserved)),
            )
        ),
        op.debounce(update_delay, scheduler=scheduler),
        op.distinct_until_changed(),
        op.as_observable(),
    )


async def parking_demo() -> list[tuple]:
    """Подать события от имитированных датчиков и службы брони."""
    sensors, reservations = Subject(), Subject()
    scheduler = AsyncIOScheduler(asyncio.get_running_loop())
    boards: list[tuple] = []
    subscription = pipeline(sensors, reservations, scheduler, update_delay=0.01).subscribe(
        boards.append,
        scheduler=scheduler,
    )
    try:
        for channel, event in (
            (sensors, Event("sensor", "A1", True)),
            (reservations, Event("reserve", "A2")),
            (sensors, Event("sensor", "A2", True)),
            (sensors, Event("sensor", "A1", False)),
        ):
            await asyncio.sleep(0.04)
            channel.on_next(event)
        await asyncio.sleep(0.02)
        sensors.on_completed()
        reservations.on_completed()
    finally:
        subscription.dispose()
    return boards


def drawing() -> None:
    """Открыть tkinter-демонстрацию рисования и событий клавиатуры."""
    import tkinter as tk

    root = tk.Tk()
    root.title("ЛР 12 — умная парковка")
    board_label = tk.Label(root)
    board_label.pack()
    canvas = tk.Canvas(root, width=640, height=380, background="white")
    canvas.pack()
    tk.Label(root, text="1–3: датчики   R: бронь A2   X: отмена   C: очистить поле").pack()
    down, move, up, keys = (Subject() for _ in range(4))
    sensor, reservations = Subject(), Subject()
    scheduler = TkinterScheduler(root)
    spot_changes = keys.pipe(
        op.map(lambda event: event.keysym),
        op.filter(lambda key: key in ("1", "2", "3")),
        op.map(lambda key: f"A{key}"),
        op.scan(
            lambda state, spot: (state[0] ^ {spot}, spot),
            (frozenset(), ""),
        ),
        op.map(lambda state: Event("sensor", state[1], state[1] in state[0])),
    ).subscribe(sensor)
    booking_changes = keys.pipe(
        op.map(lambda event: event.keysym.lower()),
        op.filter(lambda key: key in ("r", "x")),
        op.map(lambda key: Event("reserve" if key == "r" else "cancel", "A2")),
    ).subscribe(reservations)
    board = pipeline(sensor, reservations, scheduler).subscribe(
        lambda state: board_label.config(
            text=f"Свободно: {', '.join(state[0]) or '—'}  Бронь: {', '.join(state[1]) or '—'}"
        )
    )
    for widget, sequence, target in (
        (canvas, "<ButtonPress-1>", down),
        (canvas, "<B1-Motion>", move),
        (root, "<ButtonRelease-1>", up),
        (root, "<KeyPress>", keys),
    ):
        widget.bind(sequence, target.on_next)
    segments = down.pipe(
        op.flat_map(
            lambda start: move.pipe(
                op.take_until(up),
                op.start_with(start),
                op.pairwise(),
            )
        )
    )
    lines = segments.subscribe(
        lambda pair: canvas.create_line(
            pair[0].x, pair[0].y, pair[1].x, pair[1].y, width=2, fill="#254d74"
        )
    )
    clear = keys.pipe(op.filter(lambda event: event.keysym.lower() == "c")).subscribe(
        lambda _: canvas.delete("all")
    )
    try:
        root.mainloop()
    finally:
        lines.dispose()
        clear.dispose()
        board.dispose()
        spot_changes.dispose()
        booking_changes.dispose()


def collect(stream: Observable) -> list[Any]:
    """Собрать конечный синхронный поток."""
    return stream.pipe(op.to_list()).run()


def main() -> None:
    """Запустить демонстрации с фактическим выводом."""
    sources = {name: Subject() for name in ("cpu", "memory", "requests")}
    alerts, averages = monitor(**sources)
    alert_log, average_log = [], []
    alerts.subscribe(alert_log.append, on_completed=lambda: alert_log.append("|"))
    averages.subscribe(average_log.append, on_completed=lambda: average_log.append("|"))
    for name, value in server_inputs():
        sources[name].on_next(value)
    for source in sources.values():
        source.on_completed()
    print("1. Мониторинг:", alert_log, average_log)
    print("2. Корзина:", collect(basket(rx.of({"A": 10}), rx.of({"A": 2}, {"A": 3}))))
    print("   Валюта:", collect(convert(rx.of(5, 10), rx.of(470))))
    print("   Zip:", collect(rx.zip(rx.of("q1", "q2"), rx.of("r1", "r2"))))
    print("   Новости:", collect(headlines(rx.of("Дождь"), rx.of("дождь"), rx.of("Солнце"))))
    print("   Города:", collect(city_totals(rx.of(("Алматы", 10), ("Астана", 20), ("Алматы", 5)))))
    print("3. Временные операторы: см. test_rx и журнал tests.txt.")
    for seed in (1, 149):
        stream, draws = resilient(seed)
        result = collect(stream)
        print(f"4. seed={seed}:", [round(draw, 4) for draw in draws], result)
    print("   Записи:", collect(rx.of("5", "x", "7").pipe(op.map(parse))))
    print("5. Загрузчик:", asyncio.run(loader(0.85)))
    print("6. Парковка:", asyncio.run(parking_demo()))


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--gui"]:
        drawing()
    else:
        main()
