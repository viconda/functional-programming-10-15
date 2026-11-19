from collections import Counter, deque
from pathlib import Path
from statistics import median as oracle

import pytest
from hypothesis import find, given, settings
from hypothesis import strategies as st
from returns.result import Failure, Success

from schedule.exercises import (
    balance,
    chunks,
    dequeue,
    enqueue,
    median,
    merge,
    normalize,
    rle_decode,
    rle_encode,
    sort_values,
)
from schedule.libraries import (
    builtin_pipeline,
    config,
    own_result,
    result_pipeline,
    toolz_pipeline,
    windows,
)
from schedule.shell import main, parse, render, write_report

ints = st.lists(st.integers(-10000, 10000), max_size=80).map(tuple)


@pytest.fixture
def data():
    return (3, 1, 2, 2, -1)


def test_fixture_sort(data):
    assert sort_values(data) == (-1, 1, 2, 2, 3)


def test_fixture_balance(data):
    assert balance(data) == 7


@given(ints)
def test_sort_oracle(xs):
    assert sort_values(xs) == tuple(sorted(xs))


@given(ints)
def test_sort_invariant(xs):
    assert Counter(sort_values(xs)) == Counter(xs)


@given(st.text(max_size=100))
def test_rle_inverse(text):
    assert rle_decode(rle_encode(text)) == text


@given(st.text(max_size=100))
def test_normalize_idempotent(text):
    assert normalize(normalize(text)) == normalize(text)


@given(ints, ints)
def test_merge(xs, ys):
    result = merge(tuple(sorted(xs)), tuple(sorted(ys)))
    assert result == tuple(sorted(xs + ys))
    assert len(result) == len(xs) + len(ys)


@given(st.lists(st.tuples(st.booleans(), st.integers()), max_size=100))
def test_queue_model(operations):
    model, queue = deque(), ()
    for push, value in operations:
        old = queue
        if push:
            model.append(value)
            queue = enqueue(queue, value)
            assert old == queue[:-1]
        elif model:
            actual, queue = dequeue(queue)
            assert actual == model.popleft()
        else:
            with pytest.raises(ValueError, match="empty queue"):
                dequeue(queue)
        assert queue == tuple(model)


@given(ints, ints, st.integers())
def test_balance_metamorphic(xs, ys, initial):
    assert balance(xs + ys, initial) == balance(ys, balance(xs, initial))


@given(st.lists(st.integers(), min_size=1, max_size=50).map(tuple))
def test_median(xs):
    assert median(xs) == oracle(xs)


@given(ints, st.integers(1, 20))
def test_chunks_inverse(xs, n):
    assert tuple(x for part in chunks(xs, n) for x in part) == xs


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda: median(()), "empty input"),
        (lambda: chunks((1,), 0), "positive"),
        (lambda: rle_decode((("a", 0),)), "invalid RLE"),
    ],
)
def test_errors(call, message):
    with pytest.raises(ValueError, match=message):
        call()


def test_shell(tmp_path, capsys):
    source = Path(__file__).parents[1] / "sample.json"
    schedule = parse(source.read_text(encoding="utf-8"))
    out = tmp_path / "out.txt"
    write_report(out, schedule)
    assert out.read_text(encoding="utf-8") == render(schedule)
    main([str(source), "--output", str(out)])
    assert "CSE6742onl" in capsys.readouterr().out


@given(ints)
def test_library_equivalence(xs):
    assert builtin_pipeline(xs) == toolz_pipeline(xs)


def test_libraries():
    c = config({"workers": 1, "nested": {"a": [1]}}, {"workers": 2}, {"APP_WORKERS": "4"})
    assert c["workers"] == 4
    with pytest.raises(TypeError):
        c["workers"] = 5
    assert windows((1, 2, 3)) == ((1, 2), (2, 3))
    assert result_pipeline("2") == Success(0.5)
    assert isinstance(result_pipeline("0"), Failure)
    assert isinstance(result_pipeline("bad"), Failure)
    assert own_result("2") == (0.5, None)
    assert own_result("0")[0] is None


def test_minimized_bugs():
    cfg = settings(max_examples=2000, derandomize=True, database=None)

    def bad_median(xs):
        return sorted(xs)[len(xs) // 2]

    example = find(
        st.lists(st.integers(0, 5), min_size=1, max_size=6),
        lambda xs: bad_median(xs) != oracle(xs),
        settings=cfg,
    )
    assert example == [0, 1]

    def bad_chunks(xs, n):
        return [xs[i : i + n] for i in range(0, len(xs) - n, n)]

    example2 = find(
        st.lists(st.integers(0, 5), max_size=6),
        lambda xs: sum(bad_chunks(xs, 1), []) != xs,
        settings=cfg,
    )
    assert example2 == [0]
    import re

    def bad_decode(s):
        return "".join(ch * int(n) for ch, n in re.findall(r"(\D)(\d+)", s))

    example3 = find(
        st.text(alphabet="01a", min_size=1, max_size=6),
        lambda s: bad_decode("".join(ch + str(n) for ch, n in rle_encode(s))) != s,
        settings=cfg,
    )
    assert example3 == "0"
