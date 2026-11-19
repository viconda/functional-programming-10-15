import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """Детерминированный сценарий ответа имитированного сервиса."""

    number: int
    delay: float
    fails: bool


def sources(seed: int = 3) -> tuple[Source, ...]:
    """Двадцать источников, воспроизводимые задержки и 20 процентов ошибок."""
    import random

    rnd = random.Random(seed)
    return tuple(
        Source(i, (0.2 if i % 7 == 0 else rnd.uniform(0.01, 0.04)), rnd.random() < 0.2)
        for i in range(20)
    )


async def fetch(source: Source) -> int:
    """Имитировать ввод-вывод и ошибку источника."""
    await asyncio.sleep(source.delay)
    if source.fails:
        raise OSError(f"source {source.number} failed")
    return source.number * 10


async def load(
    items: tuple[Source, ...], concurrent: bool, timeout: float = 0.1
) -> list[int | BaseException]:
    """Ограничить конкурентность пятью и применить тайм-аут к запросу."""
    semaphore = asyncio.Semaphore(5)

    async def guarded(source: Source) -> int:
        async with semaphore:
            return await asyncio.wait_for(fetch(source), timeout)

    if concurrent:
        return list(await asyncio.gather(*(guarded(s) for s in items), return_exceptions=True))
    result: list[int | BaseException] = []
    for item in items:
        try:
            result.append(await guarded(item))
        except Exception as exc:
            result.append(exc)
    return result


def aggregate(results: list[int | BaseException]) -> tuple[int, int, int]:
    """Чистая агрегация успешных значений и числа ошибок."""
    values = tuple(x for x in results if isinstance(x, int))
    return sum(values), len(values), len(results) - len(values)
