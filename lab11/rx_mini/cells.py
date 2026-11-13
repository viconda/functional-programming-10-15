"""Электронная таблица с пересчётом затронутого графа."""

from __future__ import annotations

import heapq
from collections.abc import Callable
from typing import Any

from .core import Disposable
from .subjects import Subject


class Cell:
    """Ячейка со значением и фиксированными зависимостями."""

    def __init__(self, value: Any) -> None:
        self.value = value
        self._fn: Callable | None = None
        self._deps: tuple[Cell, ...] = ()
        self._children: list[Cell] = []
        self._changes = Subject()
        self._rank = 0

    @classmethod
    def formula(cls, fn: Callable, *deps: Cell) -> Cell:
        """Вычислить ячейку и зарегистрировать её в графе."""
        cell = cls(fn(*(d.value for d in deps)))
        cell._fn = fn
        cell._deps = deps
        cell._rank = 1 + max((d._rank for d in deps), default=0)
        for dep in dict.fromkeys(deps):
            dep._children.append(cell)
        return cell

    def subscribe(self, handler: Callable) -> Disposable:
        """Подписаться на изменения значения."""
        return self._changes.subscribe(handler)

    def set(self, value: Any) -> None:
        """Обновить транзитивные зависимости и оповестить подписчиков."""
        if self._fn is not None:
            raise ValueError("Нельзя присвоить значение формуле")
        if self.value == value:
            return
        self.value = value
        changed = [self]
        seen = {self}
        pending = []

        def enqueue(cell: Cell) -> None:
            for child in cell._children:
                if child not in seen:
                    heapq.heappush(pending, (child._rank, len(seen), child))
                    seen.add(child)

        enqueue(self)
        while pending:
            _, _, cell = heapq.heappop(pending)
            updated = cell._fn(*(dep.value for dep in cell._deps))
            if updated != cell.value:
                cell.value = updated
                changed.append(cell)
                enqueue(cell)
        for cell in changed:
            cell._changes.on_next(cell.value)
