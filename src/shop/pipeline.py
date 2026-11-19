from functools import reduce
from typing import Any

from .core import reduce_event
from .model import Cart, Event
from .pricing import quote


def parse_event(row: dict[str, Any]) -> Event:
    """Нормализовать поля только соответствующей операции."""
    op = str(row.get("op", ""))
    return Event(
        op,
        str(row.get("sku", "")).strip() if op in ("add", "remove") else "",
        int(row.get("price", 0)) if op == "add" else 0,
        int(row.get("qty", 1)) if op in ("add", "remove") else 1,
        str(row.get("code", "")).upper().strip() if op == "promo" else "",
    )


def process(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Лениво разобрать действия и свернуть состояние корзины."""
    return quote(reduce(reduce_event, map(parse_event, events), Cart()))
