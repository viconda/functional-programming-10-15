"""Задание 2. Швачкина Виктория, группа CSE6742onl.

Статистика, композиция, конвейер и сравнение чистоты функций.
Данные: конечные последовательности обычных чисел int/float.
"""

from collections.abc import Callable, Sequence
from functools import reduce
from typing import Any

Number = int | float
Unary = Callable[[Any], Any]


def sum_reduce(values: Sequence[Number]) -> Number:
    """Найти сумму через reduce; сумма пустой последовательности — 0."""
    return reduce(lambda total, value: total + value, values, 0)


def mean(values: Sequence[Number]) -> float:
    """Вычислить среднее непустой последовательности."""
    if not values:
        raise ValueError("Среднее пустой последовательности не определено")
    return sum_reduce(values) / len(values)


def variance(values: Sequence[Number]) -> float:
    """Найти дисперсию всей совокупности с делением на n."""
    average = mean(values)
    squared_sum = reduce(
        lambda total, value: total + (value - average) ** 2,
        values,
        0.0,
    )
    return squared_sum / len(values)


def normalize(values: Sequence[Number]) -> list[float]:
    """Вернуть min-max нормализацию; пустой вход — [], константа — 0."""
    if not values:
        return []
    low, high = min(values), max(values)
    if low == high:
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def normalize_inplace(values: list[Number]) -> None:
    """Заменить содержимое исходного списка нормализованными числами."""
    # Нечистая версия: изменяет объект, доступный вызывающему коду.
    # normalize чистая: тот же вход даёт тот же результат без мутации.
    values[:] = normalize(values)


def compose(*funcs: Unary) -> Unary:
    """Вернуть композицию справа налево; без функций — тождество."""
    def composed(value: Any) -> Any:
        """Применить сохранённые функции в обратном порядке."""
        return reduce(lambda acc, func: func(acc), reversed(funcs), value)

    return composed


def pipeline(value: Any, *funcs: Unary) -> Any:
    """Немедленно обработать значение функциями слева направо."""
    return reduce(lambda acc, func: func(acc), funcs, value)


def main() -> None:
    """Продемонстрировать статистику, порядок и побочный эффект."""
    values = [-5, 0, 5, 10]

    def add_two(x: int) -> int:
        """Добавить два к аргументу."""
        return x + 2

    def times_three(x: int) -> int:
        """Умножить аргумент на три."""
        return x * 3

    print("Исходные данные:", values)
    print("Сумма (reduce):", sum_reduce(values))
    print("Среднее:", mean(values))
    print("Дисперсия с делением на n:", variance(values))
    print("normalize(values):", normalize(values))
    print("Исходный список после чистой функции:", values)
    changed = values.copy()
    alias = changed
    normalize_inplace(changed)
    print("После normalize_inplace:", changed)
    print("Другая ссылка видит ту же мутацию:", alias)
    print("compose(+2, *3)(4):", compose(add_two, times_three)(4))
    print("pipeline(4, +2, *3):", pipeline(4, add_two, times_three))
    print("compose()(4):", compose()(4))
    print("pipeline(4):", pipeline(4))
    print("normalize([]):", normalize([]))
    print("normalize([7]):", normalize([7]))


if __name__ == "__main__":
    main()
