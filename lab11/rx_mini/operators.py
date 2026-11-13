"""Операторы для синхронных и планируемых источников."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

from .core import Observable, Observer, of

Operator = Callable[[Observable], Observable]


def map_(fn: Callable) -> Operator:
    """Преобразовать каждое значение."""
    return lambda src: Observable(lambda out: out.link(src, lambda value: out.on_next(fn(value))))


def filter_(predicate: Callable) -> Operator:
    """Оставить значения, прошедшие проверку."""

    def connect(src: Observable, out: Observer) -> None:
        def receive(value: Any) -> None:
            if predicate(value):
                out.on_next(value)

        out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))


def scan(fn: Callable, seed: Any) -> Operator:
    """Накапливать независимое состояние для каждой подписки."""

    def connect(src: Observable, out: Observer) -> None:
        state = seed

        def receive(value: Any) -> None:
            nonlocal state
            state = fn(state, value)
            out.on_next(state)

        out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))


def buffer_with_count(n: int) -> Operator:
    """Собрать неперекрывающиеся пакеты с отправкой остатка."""
    if n <= 0:
        raise ValueError(n)

    def connect(src: Observable, out: Observer) -> None:
        buffer = []

        def receive(value: Any) -> None:
            buffer.append(value)
            if len(buffer) == n:
                out.on_next(tuple(buffer))
                buffer.clear()

        def complete() -> None:
            if buffer:
                out.on_next(tuple(buffer))
            out.on_completed()

        out.link(src, receive, complete=complete)

    return lambda src: Observable(lambda out: connect(src, out))


def pairwise() -> Operator:
    """Сформировать пары соседних значений."""
    return lambda src: src.pipe(
        scan(lambda acc, v: (*acc[-1:], v), ()),
        filter_(lambda acc: len(acc) == 2),
    )


def take(n: int) -> Operator:
    """Завершить подписку после n значений."""

    def connect(src: Observable, out: Observer) -> None:
        left = n

        def receive(value: Any) -> None:
            nonlocal left
            left -= 1
            out.on_next(value)
            if left == 0:
                out.on_completed()

        if n <= 0:
            out.on_completed()
        else:
            out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))


def skip(n: int) -> Operator:
    """Пропустить до n начальных значений."""
    return lambda src: src.pipe(
        scan(lambda acc, v: (acc[0] + 1, v), (0, None)),
        filter_(lambda pair: pair[0] > n),
        map_(lambda pair: pair[1]),
    )


def identity(value: Any) -> Any:
    """Вернуть исходное значение."""
    return value


def distinct_until_changed(key: Callable = identity) -> Operator:
    """Убрать соседние повторы ключа."""

    def connect(src: Observable, out: Observer) -> None:
        missing = object()
        last = missing

        def receive(value: Any) -> None:
            nonlocal last
            current = key(value)
            if last is missing or current != last:
                last = current
                out.on_next(value)

        out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))


def take_while(predicate: Callable) -> Operator:
    """Завершиться на первом значении, не прошедшем проверку."""

    def connect(src: Observable, out: Observer) -> None:
        def receive(value: Any) -> None:
            if predicate(value):
                out.on_next(value)
            else:
                out.on_completed()

        out.link(src, receive)

    return lambda src: Observable(lambda out: connect(src, out))


def flat_map(fn: Callable[[Any], Observable]) -> Operator:
    """Объединить внутренние потоки до завершения всех подписок."""

    def connect(src: Observable, out: Observer) -> None:
        active = 1

        def complete() -> None:
            nonlocal active
            active -= 1
            if active == 0:
                out.on_completed()

        def receive(value: Any) -> None:
            nonlocal active
            inner = fn(value)
            active += 1
            out.link(inner, complete=complete)

        out.link(src, receive, complete=complete)

    return lambda src: Observable(lambda out: connect(src, out))


def merge(*sources: Observable) -> Observable:
    """Передать значения источников по мере поступления."""
    return of(*sources).pipe(flat_map(identity))


def zip_(first: Observable, second: Observable) -> Observable:
    """Составить пары по порядку поступления каждого источника."""

    def connect(out: Observer) -> None:
        queues = (deque(), deque())
        done = [False, False]

        def check() -> None:
            if any(finished and not q for finished, q in zip(done, queues)):
                out.on_completed()

        def receive(i: int, value: Any) -> None:
            queues[i].append(value)
            if all(queues):
                out.on_next(tuple(q.popleft() for q in queues))
            check()

        def complete(i: int) -> None:
            done[i] = True
            check()

        out.link(first, lambda v: receive(0, v), complete=lambda: complete(0))
        out.link(second, lambda v: receive(1, v), complete=lambda: complete(1))

    return Observable(connect)


def combine_latest(first: Observable, second: Observable) -> Observable:
    """Передать последние значения после первого события обоих источников."""

    def connect(out: Observer) -> None:
        latest = {}
        done = set()

        def receive(i: int, value: Any) -> None:
            latest[i] = value
            if len(latest) == 2:
                out.on_next((latest[0], latest[1]))

        def complete(i: int) -> None:
            done.add(i)
            if i not in latest or len(done) == 2:
                out.on_completed()

        out.link(first, lambda v: receive(0, v), complete=lambda: complete(0))
        out.link(second, lambda v: receive(1, v), complete=lambda: complete(1))

    return Observable(connect)


def start_with(value: Any) -> Operator:
    """Передать начальное значение перед подключением источника."""

    def connect(src: Observable, out: Observer) -> None:
        out.on_next(value)
        out.link(src)

    return lambda src: Observable(lambda out: connect(src, out))


def reduce_(fn: Callable, seed: Any) -> Operator:
    """Выдать итог свёртки после нормального завершения."""

    def connect(src: Observable, out: Observer) -> None:
        state = seed

        def receive(value: Any) -> None:
            nonlocal state
            state = fn(state, value)

        def complete() -> None:
            out.on_next(state)
            out.on_completed()

        out.link(src, receive, complete=complete)

    return lambda src: Observable(lambda out: connect(src, out))


def to_list() -> Operator:
    """Собрать значения подписки в обычный список."""

    def connect(src: Observable, out: Observer) -> None:
        values: list[Any] = []

        def complete() -> None:
            out.on_next(values)
            out.on_completed()

        out.link(src, values.append, complete=complete)

    return lambda src: Observable(lambda out: connect(src, out))


def count() -> Operator:
    """Посчитать значения источника."""
    return reduce_(lambda n, _: n + 1, 0)


def catch(handler: Callable[[Exception], Observable]) -> Operator:
    """При ошибке подписаться на резервный поток."""

    def connect(src: Observable, out: Observer) -> None:
        def recover(error: Exception) -> None:
            try:
                replacement = handler(error)
            except Exception as failure:
                out.on_error(failure)
            else:
                out.link(replacement)

        out.link(src, error=recover)

    return lambda src: Observable(lambda out: connect(src, out))


def retry(n: int) -> Operator:
    """Разрешить до n повторных подписок после первой попытки."""
    if n < 0:
        raise ValueError(n)

    def connect(src: Observable, out: Observer) -> None:
        remaining = n
        running = False
        pending = True

        def fail(error: Exception) -> None:
            nonlocal remaining, pending
            if not remaining:
                out.on_error(error)
                return
            remaining -= 1
            pending = True
            if not running:
                drain()

        def drain() -> None:
            nonlocal running, pending
            running = True
            try:
                while pending and not out.stopped:
                    pending = False
                    out.link(src, error=fail)
            finally:
                running = False

        drain()

    return lambda src: Observable(lambda out: connect(src, out))
