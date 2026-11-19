"""Запись уведомлений и источники с виртуальным временем."""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable
from typing import Any

from .core import Observable, Observer
from .subjects import Subject


def materialize(source: Observable) -> list[tuple]:
    """Записать уведомления N, E и C в список."""
    events = []
    source.subscribe(
        lambda value: events.append(("N", value)),
        lambda error: events.append(("E", error)),
        lambda: events.append(("C",)),
    )
    return events


class Hot(Subject):
    """Горячий источник с последовательностью ручных событий."""

    def __init__(self, *events: tuple) -> None:
        super().__init__()
        self._events = events

    def run(self) -> None:
        """Воспроизвести сценарий один раз."""
        events, self._events = self._events, ()
        for kind, *values in events:
            callback = {"N": self.on_next, "E": self.on_error, "C": self.on_completed}[kind]
            callback(*values)


def hot(*events: tuple) -> Hot:
    """Создать управляемый горячий источник."""
    return Hot(*events)


class VirtualScheduler:
    """Очередь действий с порядком регистрации на равных отметках."""

    def __init__(self) -> None:
        self.now = 0
        self._order = itertools.count()
        self._queue: list[tuple[int, int, Callable]] = []

    def schedule(self, delay: int, action: Callable[[], None]) -> Callable[[], None]:
        """Запланировать действие и вернуть функцию отмены."""
        if delay < 0:
            raise ValueError(delay)
        cancelled = False

        def cancel() -> None:
            nonlocal cancelled
            cancelled = True

        def invoke() -> None:
            if not cancelled:
                action()

        heapq.heappush(self._queue, (self.now + delay, next(self._order), invoke))
        return cancel

    def advance_to(self, time: int) -> None:
        """Выполнить действия по времени до заданной отметки включительно."""
        if time < self.now:
            raise ValueError(time)
        while self._queue and self._queue[0][0] <= time:
            self.now, _, action = heapq.heappop(self._queue)
            action()
        self.now = time


def timer(wait: int, clock: VirtualScheduler) -> Observable:
    """Создать одиночный таймер."""

    def connect(out: Observer) -> None:
        def fire() -> None:
            out.on_next(0)
            out.on_completed()

        out.subscription.add(clock.schedule(wait, fire))

    return Observable(connect)


def interval(period: int, clock: VirtualScheduler) -> Observable:
    """Выдавать номера тиков с заданным периодом."""
    if period <= 0:
        raise ValueError(period)

    def connect(out: Observer) -> None:
        index = 0
        cancel = None

        def tick() -> None:
            nonlocal index, cancel
            out.on_next(index)
            index += 1
            if not out.stopped:
                cancel = clock.schedule(period, tick)

        cancel = clock.schedule(period, tick)
        out.subscription.add(lambda: cancel())

    return Observable(connect)


def delay(wait: int, clock: VirtualScheduler) -> Callable:
    """Сдвинуть значения и нормальное завершение на заданное время."""

    def connect(src: Observable, out: Observer) -> None:
        def later(action: Callable) -> None:
            out.subscription.add(clock.schedule(wait, action))

        out.link(
            src, lambda v: later(lambda: out.on_next(v)), complete=lambda: later(out.on_completed)
        )

    return lambda src: Observable(lambda out: connect(src, out))


def debounce(wait: int, clock: VirtualScheduler) -> Callable:
    """Передать последнее значение после паузы или при завершении."""

    def connect(src: Observable, out: Observer) -> None:
        pending = ()

        def cancel():
            return None

        def flush() -> None:
            nonlocal pending
            values, pending = pending, ()
            if values:
                out.on_next(values[0])

        def receive(value: Any) -> None:
            nonlocal pending, cancel
            cancel()
            pending = (value,)
            cancel = clock.schedule(wait, flush)

        def complete() -> None:
            flush()
            out.on_completed()

        out.subscription.add(lambda: cancel())
        out.link(src, receive, complete=complete)

    return lambda src: Observable(lambda out: connect(src, out))


def throttle_first(wait: int, clock: VirtualScheduler) -> Callable:
    """Пропустить первое значение в каждом открываемом окне."""

    def connect(src: Observable, out: Observer) -> None:
        next_time = clock.now

        def receive(value: Any) -> None:
            nonlocal next_time
            if clock.now >= next_time:
                next_time = clock.now + wait
                out.on_next(value)

        out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))
