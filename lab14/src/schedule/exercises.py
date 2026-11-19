from itertools import groupby
from statistics import median as reference_median


def normalize(text: str) -> str:
    """Идемпотентная нормализация пробелов и регистра."""
    return " ".join(text.casefold().split())


def sort_values(xs: tuple[int, ...]) -> tuple[int, ...]:
    """Сортировка слиянием."""
    if len(xs) < 2:
        return xs
    middle = len(xs) // 2
    return merge(sort_values(xs[:middle]), sort_values(xs[middle:]))


def merge(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    """Слить два отсортированных кортежа за линейное время."""
    i, j = 0, 0
    result: list[int] = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    return tuple(result) + a[i:] + b[j:]


def rle_encode(text: str) -> tuple[tuple[str, int], ...]:
    """Однозначная кодировка поддерживает цифры и Unicode."""
    return tuple((ch, sum(1 for _ in run)) for ch, run in groupby(text))


def rle_decode(code: tuple[tuple[str, int], ...]) -> str:
    """Декодировать проверенные серии."""
    if any(len(ch) != 1 or n <= 0 for ch, n in code):
        raise ValueError("invalid RLE")
    return "".join(ch * n for ch, n in code)


def balance(log: tuple[int, ...], initial: int = 0) -> int:
    """Свернуть журнал целочисленных движений."""
    return initial + sum(log)


def median(xs: tuple[int, ...]) -> float:
    """Медиана с усреднением центральной пары."""
    if not xs:
        raise ValueError("empty input")
    return float(reference_median(xs))


def chunks(xs: tuple[int, ...], size: int) -> tuple[tuple[int, ...], ...]:
    """Разбить без потери хвоста."""
    if size <= 0:
        raise ValueError("size must be positive")
    return tuple(xs[i : i + size] for i in range(0, len(xs), size))


def enqueue(queue: tuple[int, ...], item: int) -> tuple[int, ...]:
    """Создать новую версию учебной персистентной очереди."""
    return (*queue, item)


def dequeue(queue: tuple[int, ...]) -> tuple[int, tuple[int, ...]]:
    """Удалить первый элемент, не меняя прежнюю очередь."""
    if not queue:
        raise ValueError("empty queue")
    return queue[0], queue[1:]
