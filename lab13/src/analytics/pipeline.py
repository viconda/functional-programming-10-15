import csv
from collections.abc import Callable
from datetime import date
from io import StringIO

from .core import summarize
from .model import Summary
from .parsing import parse_grades

Formatter = Callable[[tuple[Summary, ...], date], str]


def formatter(name: str, registry: dict[str, Formatter]) -> Callable[[Formatter], Formatter]:
    """Зарегистрировать форматтер в переданном реестре."""

    def register(fn: Formatter) -> Formatter:
        registry[name] = fn
        return fn

    return register


def make_formatters() -> dict[str, Formatter]:
    """Создать отдельный реестр без изменяемого глобального состояния."""
    registry: dict[str, Formatter] = {}

    @formatter("text", registry)
    def text(rows: tuple[Summary, ...], today: date) -> str:
        return "".join(f"{today} {r.group}: средний {r.average:.1f} [{r.status}]\n" for r in rows)

    @formatter("md", registry)
    def markdown(rows: tuple[Summary, ...], today: date) -> str:
        return f"Отчёт от {today}\n\n| Группа | Средний | Статус |\n|---|---|---|\n" + "".join(
            f"| {r.group} | {r.average:.1f} | {r.status} |\n" for r in rows
        )

    @formatter("csv", registry)
    def csv_text(rows: tuple[Summary, ...], today: date) -> str:
        out = StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("date", "group", "average", "status"))
        writer.writerows((str(today), r.group, f"{r.average:.1f}", r.status) for r in rows)
        return out.getvalue()

    return registry


def build(text: str, today: date, fmt: str = "text") -> tuple[str, str]:
    """Соединить разбор, ядро и форматирование."""
    rows = summarize(parse_grades(text))
    return make_formatters()[fmt](rows, today), f"Отчёт от {today}: групп {len(rows)}\n"
