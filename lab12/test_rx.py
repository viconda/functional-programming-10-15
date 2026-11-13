"""Проверки RxPY с виртуальным временем и фиксированными входами."""

from __future__ import annotations

import asyncio
import unittest
from collections.abc import Callable

import reactivex as rx
from reactivex import Observable
from reactivex import operators as op
from reactivex.testing import ReactiveTest, TestScheduler

from .main import (
    Event,
    basket,
    city_totals,
    collect,
    convert,
    headlines,
    loader,
    monitor,
    parse,
    pipeline,
    resilient,
    search,
)

N, C, E = ReactiveTest.on_next, ReactiveTest.on_completed, ReactiveTest.on_error


class RxTests(unittest.TestCase):
    """Сценарии времени, ошибок и парковки."""

    def check(
        self,
        name: str,
        inputs: list,
        make: Callable[[Observable, TestScheduler], Observable],
        expected: list,
    ) -> None:
        """Сравнить уведомления и напечатать их для диаграммы."""
        clock = TestScheduler()
        source = clock.create_hot_observable(*inputs)
        result = clock.start(lambda: make(source, clock))
        self.assertEqual(result.messages, expected, name)
        print(name, "| вход:", inputs, "| выход:", result.messages)

    def test_time(self) -> None:
        """Проверить пять операторов времени."""
        self.check(
            "Поиск",
            [N(210, "ал"), N(240, "алм"), N(310, "аст"), N(460, "аст "), C(600)],
            search,
            [N(450, ("астана", "астрахань")), C(600)],
        )
        self.check(
            "Оплата",
            [N(210, "a"), N(213, "b"), N(260, "c"), C(330)],
            lambda s, c: s.pipe(op.throttle_first(50, scheduler=c)),
            [N(210, "a"), N(260, "c"), C(330)],
        )
        self.check(
            "Журнал",
            [N(210, "a"), N(280, "b"), N(310, "c"), C(420)],
            lambda s, c: s.pipe(op.buffer_with_time(100, scheduler=c)),
            [N(300, ["a", "b"]), N(400, ["c"]), N(420, []), C(420)],
        )
        self.check(
            "Датчик",
            [N(210, 1), N(245, 2), N(270, 3), N(301, 4), C(340)],
            lambda s, c: s.pipe(op.sample(50, scheduler=c)),
            [N(250, 2), N(300, 3), N(350, 4), C(350)],
        )
        self.check(
            "Резерв",
            [N(220, 5), N(300, 6), C(360)],
            lambda s, c: s.pipe(op.timeout(50, rx.of(-1), scheduler=c)),
            [N(220, 5), N(270, -1), C(270)],
        )

    def test_parking(self) -> None:
        """Проверить семь сценариев парковки с точным временем."""
        full = (("A1", "A2", "A3"), ())
        a_busy = (("A2", "A3"), ())
        b_reserved = (("A1", "A3"), ("A2",))
        b_busy = (("A1", "A3"), ())
        cases = (
            ("Начальное табло", [], [], [N(210, full)]),
            (
                "Датчик и освобождение",
                [N(230, Event("sensor", "A1", True)), N(260, Event("sensor", "A1"))],
                [],
                [N(210, full), N(240, a_busy), N(270, full)],
            ),
            (
                "Бронь и отмена",
                [],
                [N(230, Event("reserve", "A2")), N(260, Event("cancel", "A2"))],
                [N(210, full), N(240, b_reserved), N(270, full)],
            ),
            (
                "Запрет брони занятого",
                [N(230, Event("sensor", "A1", True))],
                [N(260, Event("reserve", "A1"))],
                [N(210, full), N(240, a_busy)],
            ),
            (
                "Заезд по брони",
                [N(260, Event("sensor", "A2", True))],
                [N(230, Event("reserve", "A2"))],
                [N(210, full), N(240, b_reserved), N(270, b_busy)],
            ),
            (
                "Фильтр неизвестных мест",
                [N(230, Event("sensor", "B4", True))],
                [N(240, Event("reserve", "B4"))],
                [N(210, full)],
            ),
            (
                "Пакет изменений",
                [N(230, Event("sensor", "A1", True)), N(234, Event("sensor", "A1"))],
                [],
                [N(210, full)],
            ),
        )
        for name, sensors, reservations, expected in cases:
            with self.subTest(name=name):
                clock = TestScheduler()
                s = clock.create_hot_observable(*sensors, C(350))
                r = clock.create_hot_observable(*reservations, C(350))
                output = clock.start(lambda: pipeline(s, r, clock, update_delay=10))
                self.assertEqual(output.messages, [*expected, C(350)])
                print(
                    name,
                    "| датчики:",
                    sensors,
                    "| бронь:",
                    reservations,
                    "| табло:",
                    output.messages,
                )

    def test_combinations(self) -> None:
        """Проверить фактическую семантику пяти комбинаций."""
        self.check(
            "Корзина",
            [N(210, {"A": 10}), N(240, {"A": 15}), C(300)],
            lambda s, c: basket(
                s, c.create_hot_observable(N(220, {"A": 2}), N(260, {"A": 3}), C(300))
            ),
            [N(220, 20), N(240, 30), N(260, 45), C(300)],
        )
        self.check(
            "Валюта",
            [N(210, 10), N(230, 5), N(260, 10), C(300)],
            lambda s, c: convert(s, c.create_hot_observable(N(220, 470), N(240, 480), C(300))),
            [N(230, 2350), N(260, 4800), C(300)],
        )
        self.check(
            "Запросы",
            [N(210, "q1"), N(220, "q2"), C(300)],
            lambda s, c: rx.zip(s, c.create_hot_observable(N(235, "r1"), N(255, "r2"), C(310))),
            [N(235, ("q1", "r1")), N(255, ("q2", "r2")), C(300)],
        )
        self.check(
            "Новости",
            [N(210, "Дождь"), C(300)],
            lambda s, c: headlines(
                s,
                c.create_hot_observable(N(220, "дождь"), C(300)),
                c.create_hot_observable(N(230, "Солнце"), C(300)),
            ),
            [N(210, "Дождь"), N(230, "Солнце"), C(300)],
        )
        self.check(
            "Города",
            [N(210, ("Алматы", 10)), N(220, ("Астана", 20)), N(230, ("Алматы", 5)), C(300)],
            lambda s, _: city_totals(s),
            [N(210, ("Алматы", 10)), N(220, ("Астана", 20)), N(230, ("Алматы", 15)), C(300)],
        )

    def test_errors(self) -> None:
        """Проверить нормальный повтор, резерв, ошибку и ошибку как значение."""
        for seed, want, count in ((1, "основной", 2), (149, "резервный", 3)):
            stream, draws = resilient(seed)
            self.assertEqual(collect(stream), [want])
            self.assertEqual(len(draws), count)
        failure = ValueError("отказ")
        self.check(
            "CPU ошибка",
            [N(210, 95), E(260, failure)],
            lambda s, c: monitor(s, c.create_hot_observable(N(220, 85), C(300)), rx.empty())[0],
            [N(220, True), E(260, failure)],
        )
        items = collect(rx.of("1", "x", "2").pipe(op.map(parse)))
        self.assertEqual([item.value for item in items], [1, None, 2])
        self.assertTrue(items[1].error)

    def test_loader_stop(self) -> None:
        """Остановить загрузчик без незакрытых задач."""

        async def check() -> None:
            result = await loader(0.58)
            self.assertEqual(result, [(1, 20.0), (2, 20.5)])
            self.assertEqual(len(asyncio.all_tasks()), 1)
            self.assertEqual(await loader(0), [])

        asyncio.run(check())
