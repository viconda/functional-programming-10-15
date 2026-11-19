import csv

from .model import Grade


def parse_grades(text: str) -> tuple[Grade, ...]:
    """Разобрать CSV без обращения к файлам."""
    return tuple(Grade(r["group"], int(r["score"])) for r in csv.DictReader(text.splitlines()))
