"""Мраморные тесты собственной реактивной библиотеки."""

from __future__ import annotations

import unittest

from .demo import Auction, Bid, auction
from .rx_mini import operators as op
from .rx_mini.core import empty, from_iterable, of, throw
from .rx_mini.subjects import Subject
from .rx_mini.testing import (
    VirtualScheduler,
    debounce,
    delay,
    hot,
    interval,
    materialize,
    throttle_first,
)


class MiniTests(unittest.TestCase):
    """Проверки значений, завершения, ошибок и отписок."""

    def test_sources_and_operators(self) -> None:
        """Прогнать два независимых сценария для каждого оператора."""
        cases = (
            ("of", of(1, 2), [1, 2], of(), []),
            ("iterable", from_iterable(range(3)), [0, 1, 2], from_iterable([]), []),
            ("empty", empty(), [], empty().pipe(op.count()), [0]),
            ("map", of(1, 2).pipe(op.map_(str)), ["1", "2"], empty().pipe(op.map_(str)), []),
            (
                "scan",
                of(1, 2).pipe(op.scan(int.__add__, 0)),
                [1, 3],
                of(2).pipe(op.scan(int.__add__, 4)),
                [6],
            ),
            (
                "buffer",
                of(1, 2, 3).pipe(op.buffer_with_count(2)),
                [(1, 2), (3,)],
                empty().pipe(op.buffer_with_count(2)),
                [],
            ),
            (
                "pairwise",
                of(1, 2, 3).pipe(op.pairwise()),
                [(1, 2), (2, 3)],
                of(1).pipe(op.pairwise()),
                [],
            ),
            (
                "flat_map",
                of(1, 2).pipe(op.flat_map(lambda x: of(x, -x))),
                [1, -1, 2, -2],
                of(1).pipe(op.flat_map(lambda _: empty())),
                [],
            ),
            (
                "filter",
                of(1, 2).pipe(op.filter_(lambda x: x > 1)),
                [2],
                of(1).pipe(op.filter_(lambda _: False)),
                [],
            ),
            ("take", of(1, 2).pipe(op.take(1)), [1], of(1).pipe(op.take(0)), []),
            ("skip", of(1, 2).pipe(op.skip(1)), [2], of(1).pipe(op.skip(3)), []),
            (
                "distinct",
                of(1, 1, 2, 1).pipe(op.distinct_until_changed()),
                [1, 2, 1],
                of("A", "a", "B").pipe(op.distinct_until_changed(str.lower)),
                ["A", "B"],
            ),
            (
                "take_while",
                of(1, 5, 2).pipe(op.take_while(lambda x: x < 3)),
                [1],
                of(5, 1).pipe(op.take_while(lambda x: x < 3)),
                [],
            ),
            ("merge", op.merge(of(1), of(2)), [1, 2], op.merge(empty(), of(2)), [2]),
            ("zip", op.zip_(of(1, 2), of("a")), [(1, "a")], op.zip_(empty(), of(1)), []),
            (
                "combine_latest",
                op.combine_latest(of(1, 2), of("a", "b")),
                [(2, "a"), (2, "b")],
                op.combine_latest(empty(), of(1)),
                [],
            ),
            (
                "start_with",
                of(2).pipe(op.start_with(1)),
                [1, 2],
                empty().pipe(op.start_with(1)),
                [1],
            ),
            (
                "reduce",
                of(1, 2).pipe(op.reduce_(int.__add__, 1)),
                [4],
                empty().pipe(op.reduce_(int.__add__, 1)),
                [1],
            ),
            ("list", of(1, 2).pipe(op.to_list()), [[1, 2]], empty().pipe(op.to_list()), [[]]),
            ("count", of(1, 2).pipe(op.count()), [2], empty().pipe(op.count()), [0]),
            (
                "catch",
                throw(ValueError()).pipe(op.catch(lambda _: of(8))),
                [8],
                of(3).pipe(op.catch(lambda _: of(8))),
                [3],
            ),
            ("retry", of(1).pipe(op.retry(1)), [1], empty().pipe(op.retry(0)), []),
        )
        for name, first, a, second, b in cases:
            for source, expected in ((first, a), (second, b)):
                with self.subTest(operator=name, expected=expected):
                    self.assertEqual(materialize(source), [("N", v) for v in expected] + [("C",)])

    def test_errors(self) -> None:
        """Проверить ошибки источника, функции и резервного обработчика."""
        err = ValueError("сломано")
        self.assertEqual(materialize(throw(err)), [("E", err)])
        self.assertEqual(materialize(throw(err).pipe(op.retry(3))), [("E", err)])
        self.assertEqual(materialize(throw(err).pipe(op.to_list())), [("E", err)])
        self.assertEqual(materialize(of(0, 1).pipe(op.map_(lambda x: 1 / x)))[0][0], "E")
        stream = hot(("N", 0), ("N", 1), ("C",))
        result = materialize(stream.pipe(op.map_(lambda x: 1 / x)))
        stream.run()
        self.assertEqual([e[0] for e in result], ["E"])

    def test_disposal(self) -> None:
        """Проверить остановку синхронного источника и отписку от Subject."""
        consumed = []
        self.assertEqual(
            materialize(
                from_iterable((consumed.append(i) or i for i in range(10))).pipe(op.take(2))
            ),
            [("N", 0), ("N", 1), ("C",)],
        )
        self.assertEqual(consumed, [0, 1])
        stream = hot(("N", 7), ("N", 8), ("C",), ("N", 9))
        self.assertEqual(materialize(stream.pipe(op.take(1))), [])
        results = materialize(stream.pipe(op.take(1)))
        stream.run()
        self.assertEqual(results, [("N", 7), ("C",)])
        self.assertEqual(materialize(stream), [("C",)])

    def test_virtual_operators(self) -> None:
        """Сравнить абсолютное время значений и завершения."""
        for make, expected in (
            (lambda s, c: s.pipe(delay(3, c)), [(4, "a"), (5, "b"), (12, "c"), (15, "|")]),
            (lambda s, c: s.pipe(debounce(4, c)), [(6, "b"), (12, "c"), (12, "|")]),
            (lambda s, c: s.pipe(throttle_first(4, c)), [(1, "a"), (9, "c"), (12, "|")]),
            (lambda s, c: interval(3, c).pipe(op.take(3)), [(3, 0), (6, 1), (9, 2), (9, "|")]),
        ):
            clock, subject, events = VirtualScheduler(), Subject(), []

            def record(value: object) -> None:
                events.append((clock.now, value))

            make(subject, clock).subscribe(record, on_completed=lambda: record("|"))
            for time, value in ((1, "a"), (2, "b"), (9, "c")):
                clock.schedule(time, lambda v=value: subject.on_next(v))
            clock.schedule(12, subject.on_completed)
            clock.advance_to(30)
            self.assertEqual(events, expected)
            print("Время:", expected)

    def test_auction_marbles(self) -> None:
        """Проверить повышение, равенство, пустой аукцион и позднюю ставку."""
        a, b = Bid("Алия", 100), Bid("Нур", 120)
        for events, expected in (
            (
                ((2, a), (5, b)),
                [(0, Auction()), (2, Auction(a)), (5, Auction(b)), (10, Auction(b, True))],
            ),
            (
                ((2, a), (5, Bid("Нур", 100))),
                [(0, Auction()), (2, Auction(a)), (10, Auction(a, True))],
            ),
            (((11, a),), [(0, Auction()), (10, Auction(None, True))]),
            (((10, a),), [(0, Auction()), (10, Auction(None, True))]),
        ):
            clock, bids = VirtualScheduler(), Subject()
            states, done = [], []
            auction(bids, clock, 10).subscribe(
                lambda state: states.append((clock.now, state)),
                on_completed=lambda: done.append(clock.now),
            )
            for at, bid in events:
                clock.schedule(at, lambda v=bid: bids.on_next(v))
            clock.advance_to(20)
            self.assertEqual(states, expected)
            self.assertEqual(done, [10])
            print("Аукцион:", states, "|", done[0])
