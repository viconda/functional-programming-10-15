import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "previous", Path(__file__).parents[1] / "previous_task1.py"
)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


@pytest.mark.parametrize("score, expected", [(0, "F"), (49, "F"), (50, "D"), (75, "B"), (100, "A")])
def test_letter(score, expected):
    assert previous.to_letter(score) == expected


@pytest.mark.parametrize(
    "xs, expected", [([], []), ([49], []), ([50], [50]), ([0, 100], [100]), ([75, 50], [75, 50])]
)
def test_passed(xs, expected):
    assert previous.passed_scores(xs) == expected


@pytest.mark.parametrize(
    "xs, expected", [([], []), ([49], []), ([50], ["D"]), ([100], ["A"]), ([75, 50], ["B", "D"])]
)
def test_map(xs, expected):
    assert previous.letters_map(xs) == expected


@pytest.mark.parametrize(
    "xs, expected", [([], []), ([49], []), ([50], ["D"]), ([100], ["A"]), ([75, 50], ["B", "D"])]
)
def test_comprehension(xs, expected):
    assert previous.letters_comp(xs) == expected


@pytest.mark.parametrize(
    "xs, expected",
    [([], []), ([""], [""]), ([" A "], ["A"]), (["A  B"], ["A B"]), (["a\tb"], ["a b"])],
)
def test_clean(xs, expected):
    assert previous.clean_names(xs) == expected


@pytest.mark.parametrize(
    "xs, expected",
    [([], []), ([""], []), (["Ли"], []), (["A B"], ["A B"]), ([" Пак София "], ["Пак София"])],
)
def test_valid(xs, expected):
    assert previous.valid_names(xs) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("A B", "A B."),
        ("Пак София", "Пак С."),
        ("Ли Анна", "Ли А."),
        ("Я И", "Я И."),
        ("А Б В", "А Б."),
    ],
)
def test_format_one(text, expected):
    assert previous.format_name(text) == expected


@pytest.mark.parametrize(
    "xs, expected",
    [
        ([], []),
        ([""], []),
        (["Ли"], []),
        (["Пак София"], ["Пак С."]),
        (["Б Б", "А А"], ["А А.", "Б Б."]),
    ],
)
def test_format_many(xs, expected):
    assert previous.format_names(xs) == expected
