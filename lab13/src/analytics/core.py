from .model import Grade, Summary


def summarize(rows: tuple[Grade, ...]) -> tuple[Summary, ...]:
    """Рассчитать средние, не меняя вход."""

    def one(group: str) -> Summary:
        scores = tuple(r.score for r in rows if r.group == group)
        avg = sum(scores) / len(scores)
        return Summary(group, avg, "ОК" if avg >= 70 else "РИСК")

    return tuple(map(one, sorted({r.group for r in rows})))


def is_prime(n: int) -> bool:
    """Проверить простоту целого числа."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % d for d in range(3, int(n**0.5) + 1, 2))


def count_primes(values: tuple[int, ...]) -> int:
    """Свернуть пакет чисел в количество простых."""
    return sum(map(is_prime, values))


def square_batch(values: tuple[int, ...]) -> tuple[int, ...]:
    """Независимый шаг для универсального конвейера."""
    return tuple(x * x for x in values)
