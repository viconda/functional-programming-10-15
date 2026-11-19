import argparse
import json
from pathlib import Path

from .core import Lesson, add


def parse(text: str) -> tuple[Lesson, ...]:
    """Собрать проверенное расписание из JSON."""
    schedule: tuple[Lesson, ...] = ()
    for row in json.loads(text):
        schedule = add(schedule, Lesson(**row))
    return schedule


def render(schedule: tuple[Lesson, ...]) -> str:
    """Текстовое представление расписания."""
    return "\n".join(
        f"День {x.day} {x.start:04d}-{x.end:04d} {x.room} {x.group} {x.teacher}" for x in schedule
    )


def write_report(path: Path, schedule: tuple[Lesson, ...]) -> None:
    """Записать UTF-8 отчёт."""
    path.write_text(render(schedule), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    """CLI с входным JSON и необязательным файлом отчёта."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", type=Path, nargs="?", default=Path(__file__).parents[2] / "sample.json"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = parse(args.input.read_text(encoding="utf-8"))
    print(render(result))
    if args.output:
        write_report(args.output, result)
