from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import TypeVar

T = TypeVar("T")


def chunks(xs: tuple[T, ...], size: int) -> tuple[tuple[T, ...], ...]:
    """Сохранить все элементы при разбиении."""
    if size <= 0:
        raise ValueError("size must be positive")
    return tuple(xs[i : i + size] for i in range(0, len(xs), size))


def apply_steps(
    data: tuple[int, ...], steps: tuple[Callable[[tuple[int, ...]], tuple[int, ...]], ...]
) -> tuple[int, ...]:
    """Применить весь конвейер к одному фрагменту."""
    for step in steps:
        data = step(data)
    return data


def parallel_pipeline(
    steps: tuple[Callable[[tuple[int, ...]], tuple[int, ...]], ...],
    data: tuple[int, ...],
    workers: int,
) -> tuple[int, ...]:
    """Конвейер для независимых элементов с сохранением порядка."""
    with ProcessPoolExecutor(max_workers=workers) as pool:
        parts = chunks(data, max(1, (len(data) + workers - 1) // workers))
        return tuple(x for part in pool.map(partial(apply_steps, steps=steps), parts) for x in part)
