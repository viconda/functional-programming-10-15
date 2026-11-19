"""Синхронное ядро Observable и управление подписками."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

Action = Callable[[], None]


class Disposable:
    """Идемпотентная подписка с поддержкой поздней регистрации очистки."""

    def __init__(self) -> None:
        self.closed = False
        self._actions: list[Action] = []

    def add(self, action: Action) -> None:
        """Зарегистрировать очистку или выполнить её для закрытой подписки."""
        if self.closed:
            action()
        else:
            self._actions.append(action)

    def dispose(self) -> None:
        """Закрыть подписку и выполнить очистку."""
        if not self.closed:
            self.closed = True
            actions, self._actions = self._actions, []
            for action in reversed(actions):
                action()


def ignore(*args: Any) -> None:
    """Пропустить уведомление."""


class Observer:
    """Три обработчика и общее состояние остановки."""

    def __init__(
        self,
        next_: Callable = ignore,
        error: Callable = ignore,
        complete: Action = ignore,
        stopped: Callable[[], bool] = lambda: False,
    ) -> None:
        self.subscription = Disposable()
        self._next = next_
        self._error = error
        self._complete = complete
        self._stopped = stopped

    @property
    def stopped(self) -> bool:
        """Проверить отмену и терминальное состояние."""
        return self.subscription.closed or self._stopped()

    def on_next(self, value: Any) -> None:
        """Доставить значение активной подписке."""
        if not self.stopped:
            self._next(value)

    def on_error(self, error: Exception) -> None:
        """Завершить поток ошибкой."""
        if not self.stopped:
            self.subscription.dispose()
            self._error(error)

    def on_completed(self) -> None:
        """Нормально завершить поток."""
        if not self.stopped:
            self.subscription.dispose()
            self._complete()

    def link(
        self,
        source: Observable,
        next_: Callable | None = None,
        error: Callable | None = None,
        complete: Action | None = None,
    ) -> Disposable:
        """Подключить дочерний источник и связать отмену."""
        child = Observer(
            next_ or self.on_next,
            error or self.on_error,
            complete or self.on_completed,
            lambda: self.stopped,
        )
        if not self.stopped:
            self.subscription.add(child.subscription.dispose)
            source.connect(child)
        return child.subscription


class Observable:
    """Функция подключения источника к наблюдателю."""

    def __init__(self, connect: Callable[[Observer], None]) -> None:
        self._connect = connect

    def connect(self, observer: Observer) -> None:
        """Запустить источник и передать ошибку в терминальный канал."""
        try:
            self._connect(observer)
        except Exception as error:
            if observer.stopped:
                raise
            observer.on_error(error)

    def subscribe(
        self,
        on_next: Callable = ignore,
        on_error: Callable = ignore,
        on_completed: Action = ignore,
    ) -> Disposable:
        """Подключить обработчики и вернуть подписку."""
        observer = Observer(on_next, on_error, on_completed)
        self.connect(observer)
        return observer.subscription

    def pipe(self, *operators: Callable[[Observable], Observable]) -> Observable:
        """Применить операторы слева направо."""
        result = self
        for operator in operators:
            result = operator(result)
        return result


def from_iterable(values: Iterable[Any]) -> Observable:
    """Итерировать значения по запросу при каждой подписке."""

    def connect(out: Observer) -> None:
        iterator = iter(values)
        while not out.stopped:
            try:
                value = next(iterator)
            except StopIteration:
                out.on_completed()
                return
            out.on_next(value)

    return Observable(connect)


def of(*values: Any) -> Observable:
    """Создать холодный поток заданных значений."""
    return from_iterable(values)


def empty() -> Observable:
    """Создать поток без значений."""
    return of()


def throw(error: Exception) -> Observable:
    """Создать поток, завершающийся ошибкой."""
    return Observable(lambda out: out.on_error(error))
