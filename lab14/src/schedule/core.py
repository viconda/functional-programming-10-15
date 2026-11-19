from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Lesson:
    """Занятие, полуоткрытый интервал минут в пределах дня."""

    day: int
    start: int
    end: int
    room: str
    group: str
    teacher: str


def validate(lesson: Lesson) -> Lesson:
    """Проверить поля занятия."""
    if not 1 <= lesson.day <= 7 or not 0 <= lesson.start < lesson.end <= 1440:
        raise ValueError("invalid interval")
    if not all(x.strip() for x in (lesson.room, lesson.group, lesson.teacher)):
        raise ValueError("empty resource")
    return lesson


def overlap(a: Lesson, b: Lesson) -> bool:
    """Касание границ не считается пересечением."""
    return a.day == b.day and a.start < b.end and b.start < a.end


def conflict(a: Lesson, b: Lesson) -> bool:
    """Совпавший ресурс занят только при пересечении времени."""
    return overlap(a, b) and (a.room == b.room or a.group == b.group or a.teacher == b.teacher)


def conflicts(schedule: tuple[Lesson, ...]) -> tuple[tuple[int, int], ...]:
    """Вернуть индексы конфликтующих пар."""
    return tuple(
        (i, j)
        for i, a in enumerate(schedule)
        for j, b in enumerate(schedule)
        if i < j and conflict(a, b)
    )


def add(schedule: tuple[Lesson, ...], lesson: Lesson) -> tuple[Lesson, ...]:
    """Добавить занятие или вернуть ошибку, сохранив прежнюю версию."""
    validate(lesson)
    if any(conflict(old, lesson) for old in schedule):
        raise ValueError("resource conflict")
    return tuple(sorted((*schedule, lesson)))


def remove(schedule: tuple[Lesson, ...], lesson: Lesson) -> tuple[Lesson, ...]:
    """Удалить занятие, отсутствующее занятие не меняет результат."""
    return tuple(x for x in schedule if x != lesson)
