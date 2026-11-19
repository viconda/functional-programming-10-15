from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from schedule.core import Lesson, add, conflict, conflicts, overlap, remove, validate

base = Lesson(1, 60, 120, "A", "G", "T")
lessons = st.builds(
    Lesson,
    st.integers(1, 7),
    st.integers(0, 1300),
    st.just(1440),
    st.sampled_from(["A", "B"]),
    st.sampled_from(["G", "H"]),
    st.sampled_from(["T", "U"]),
)


@given(lessons, lessons)
def test_overlap_symmetric(a, b):
    assert overlap(a, b) == overlap(b, a)


@given(lessons, lessons)
def test_conflict_symmetric(a, b):
    assert conflict(a, b) == conflict(b, a)


@given(lessons)
def test_roundtrip(lesson):
    assert remove(add((), lesson), lesson) == ()


@given(lessons)
def test_original_unchanged(lesson):
    original = ()
    add(original, lesson)
    assert original == ()


@given(lessons)
def test_reject_duplicate(lesson):
    with pytest.raises(ValueError, match="resource conflict"):
        add((lesson,), lesson)


@given(lessons, st.integers(1, 7))
def test_other_day(lesson, day):
    if day != lesson.day:
        assert not conflict(lesson, replace(lesson, day=day))


def test_boundaries():
    assert not conflict(base, replace(base, start=120, end=130))
    assert conflicts((base, base)) == ((0, 1),)
    assert not conflict(base, replace(base, room="B", group="H", teacher="U"))
    for bad in (replace(base, day=0), replace(base, start=120), replace(base, room=" ")):
        with pytest.raises(ValueError):
            validate(bad)


class ScheduleMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.schedule = ()
        self.model = []

    @rule(lesson=lessons)
    def insert(self, lesson):
        # Независимая модель проверяет интервалы и общие ресурсы явно.
        collision = any(
            x.day == lesson.day
            and max(x.start, lesson.start) < min(x.end, lesson.end)
            and bool(
                {("r", x.room), ("g", x.group), ("t", x.teacher)}
                & {("r", lesson.room), ("g", lesson.group), ("t", lesson.teacher)}
            )
            for x in self.model
        )
        if collision:
            with pytest.raises(ValueError):
                add(self.schedule, lesson)
        else:
            self.schedule = add(self.schedule, lesson)
            self.model.append(lesson)

    @rule()
    def delete(self):
        if self.model:
            item = self.model.pop()
            self.schedule = remove(self.schedule, item)

    @invariant()
    def consistent(self):
        assert self.schedule == tuple(sorted(self.model))
        assert conflicts(self.schedule) == ()


TestScheduleMachine = ScheduleMachine.TestCase
