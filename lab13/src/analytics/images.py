from concurrent.futures import ProcessPoolExecutor
from functools import partial

Matrix = tuple[tuple[int, ...], ...]


def validate(image: Matrix) -> None:
    """Проверить прямоугольную матрицу значений 0..255."""
    if not image or not image[0] or any(len(row) != len(image[0]) for row in image):
        raise ValueError("image must be nonempty and rectangular")
    if any(not 0 <= x <= 255 for row in image for x in row):
        raise ValueError("pixel must be in 0..255")


def sample(image: Matrix, y: int, x: int) -> int:
    """Продлить границу ближайшим пикселем."""
    return image[min(max(y, 0), len(image) - 1)][min(max(x, 0), len(image[0]) - 1)]


def filter_rows(bounds: tuple[int, int], image: Matrix, mode: str) -> Matrix:
    """Рассчитать полоску с доступом к ореолу исходной матрицы."""

    def pixel(y: int, x: int) -> int:
        if mode == "blur":
            return sum(sample(image, y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) // 9
        laplace = 4 * sample(image, y, x) - sum(
            sample(image, y + dy, x + dx) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )
        return min(255, abs(laplace))

    return tuple(tuple(pixel(y, x) for x in range(len(image[0]))) for y in range(*bounds))


def transform(image: Matrix, mode: str = "blur", workers: int = 1) -> Matrix:
    """Фильтр размытия или Лапласа, последовательно или полосками."""
    validate(image)
    if mode not in ("blur", "edges") or workers < 1:
        raise ValueError("invalid mode or workers")
    if workers == 1:
        return filter_rows((0, len(image)), image, mode)
    size = max(1, (len(image) + workers - 1) // workers)
    bounds = tuple((i, min(i + size, len(image))) for i in range(0, len(image), size))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return tuple(
            row
            for part in pool.map(partial(filter_rows, image=image, mode=mode), bounds)
            for row in part
        )
