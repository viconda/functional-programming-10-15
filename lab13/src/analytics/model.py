from dataclasses import dataclass


@dataclass(frozen=True)
class Grade:
    """Неизменяемая оценка студента."""

    group: str
    score: int


@dataclass(frozen=True)
class Summary:
    """Средний балл группы."""

    group: str
    average: float
    status: str
