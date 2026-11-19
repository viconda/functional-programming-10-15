import asyncio
from datetime import date

import pytest

from analytics.async_io import Source, aggregate, load
from analytics.core import count_primes, is_prime, summarize
from analytics.images import sample, transform, validate
from analytics.model import Grade
from analytics.parallel import chunks
from analytics.parsing import parse_grades
from analytics.pipeline import build, make_formatters
from analytics.shell import run


@pytest.mark.parametrize(
    "n, expected", [(0, False), (1, False), (2, True), (3, True), (4, False), (97, True)]
)
def test_prime(n, expected):
    assert is_prime(n) == expected


def test_grades():
    rows = parse_grades("group,score\nA,60\nA,80\nB,69\n")
    assert summarize(rows)[0].status == "ОК"
    assert summarize(rows)[1].status == "РИСК"
    assert summarize(()) == ()
    assert rows[0] == Grade("A", 60)


def test_shell():
    saved, output = [], []
    run(lambda: "group,score\nA,70\n", lambda: date(2026, 1, 1), saved.append, output.append)
    assert saved == ["Отчёт от 2026-01-01: групп 1\n"]
    assert output == ["2026-01-01 A: средний 70.0 [ОК]"]


@pytest.mark.parametrize("fmt", ["text", "csv", "md"])
def test_formats(fmt):
    text, header = build("group,score\nA,70\n", date(2026, 1, 1), fmt)
    assert "A" in text and "групп 1" in header
    assert len(make_formatters()) == 3


def test_chunks():
    assert chunks((), 3) == ()
    assert chunks((1, 2, 3), 2) == ((1, 2), (3,))
    assert count_primes((2, 3, 4)) == 2
    with pytest.raises(ValueError, match="positive"):
        chunks((1,), 0)


@pytest.mark.parametrize("image", [(), ((),), ((1, 2), (3,)), ((256,),), ((-1,),)])
def test_invalid_image(image):
    with pytest.raises(ValueError):
        validate(image)


@pytest.mark.parametrize("mode", ["blur", "edges"])
def test_image_parallel(mode):
    image = ((0, 0, 0), (0, 255, 0), (0, 0, 0))
    before = tuple(image)
    assert transform(image, mode, 2) == transform(image, mode)
    assert image == before


@pytest.mark.parametrize("value", [0, 1, 127, 255])
def test_constant(value):
    image = ((value, value), (value, value))
    assert transform(image) == image
    assert transform(image, "edges") == ((0, 0), (0, 0))


def test_single():
    assert transform(((255,),)) == ((255,),)
    assert sample(((1, 2),), -1, 8) == 2
    with pytest.raises(ValueError, match="invalid"):
        transform(((1,),), "oops")


def test_async():
    items = (Source(1, 0, False), Source(2, 0, True), Source(3, 0.05, False))
    a = asyncio.run(load(items, False, 0.01))
    b = asyncio.run(load(items, True, 0.01))
    assert aggregate(a) == aggregate(b) == (10, 1, 2)


def test_universal_pipeline():
    from analytics.async_io import sources
    from analytics.core import square_batch
    from analytics.parallel import apply_steps, parallel_pipeline

    assert apply_steps((1, 2), (square_batch, square_batch)) == (1, 16)
    assert parallel_pipeline((square_batch,), (1, 2, 3, 4), 2) == (1, 4, 9, 16)
    assert parallel_pipeline((), (), 2) == ()
    assert sources(3) == sources(3)
