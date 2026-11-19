from collections.abc import Callable
from datetime import date

from .pipeline import build


def run(
    load: Callable[[], str],
    now: Callable[[], date],
    save: Callable[[str], None],
    emit: Callable[[str], None] = print,
    fmt: str = "text",
) -> str:
    """Внедрить эффекты чтения, даты, записи и вывода."""
    rendered, header = build(load(), now(), fmt)
    emit(rendered.rstrip("\n"))
    save(header if fmt == "text" else rendered)
    return rendered
