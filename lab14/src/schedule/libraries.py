from collections.abc import Mapping
from typing import Any

from pyrsistent import freeze
from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Result, safe
from toolz import pipe
from toolz.curried import filter as tfilter
from toolz.curried import groupby, sliding_window, valmap
from toolz.curried import map as tmap


def builtin_pipeline(values: tuple[int, ...]) -> dict[int, int]:
    """Обычный конвейер: квадрат, фильтр и сумма по чётности."""
    squared = tuple(x * x for x in values if x >= 0)
    return {
        k: sum(x for x in squared if x % 2 == k) for k in (0, 1) if any(x % 2 == k for x in squared)
    }


def toolz_pipeline(values: tuple[int, ...]) -> Any:
    """Эквивалентная композиция curried map/filter/groupby/valmap."""
    return pipe(
        values,
        tfilter(lambda x: x >= 0),
        tmap(lambda x: x * x),
        groupby(lambda x: x % 2),
        valmap(sum),
    )


def windows(values: tuple[int, ...]) -> Any:
    """Скользящие пары через curried sliding_window."""
    return tuple(pipe(values, sliding_window(2)))


def config(
    defaults: Mapping[str, object], file: Mapping[str, object], env: Mapping[str, str]
) -> Any:
    """Приоритет env > файл > defaults, результат рекурсивно заморожен."""
    overrides = {
        k[4:].lower(): int(v) if v.isdecimal() else v
        for k, v in env.items()
        if k.startswith("APP_")
    }
    return freeze({**defaults, **file, **overrides})


@safe
def parse_positive(text: str) -> int:
    """Обернуть исключения в returns.Result."""
    value = int(text)
    if value <= 0:
        raise ValueError("positive required")
    return value


def reciprocal(value: int) -> Result[float, Exception]:
    """Успешный результат второго шага."""
    return safe(lambda: 1 / value)()


def result_pipeline(text: str) -> Result[float, Exception]:
    """Соединить шаги flow и bind, сохранив первую ошибку."""
    return flow(text, parse_positive, bind(reciprocal))


def own_result(text: str) -> tuple[float | None, str | None]:
    """Простой аналог Result с явной проверкой ошибки."""
    try:
        value = int(text)
        if value <= 0:
            raise ValueError("positive required")
        return 1 / value, None
    except ValueError as exc:
        return None, str(exc)
