"""Горячий источник с рассылкой текущим подписчикам."""

from typing import Any

from .core import Observable, Observer


class Subject(Observable):
    """Наблюдатель и Observable с общим терминальным состоянием."""

    def __init__(self) -> None:
        self._observers: dict[int, Observer] = {}
        self._done = False
        self._error: Exception | None = None
        super().__init__(self._register)

    def _register(self, observer: Observer) -> None:
        if self._done:
            if self._error is None:
                observer.on_completed()
            else:
                observer.on_error(self._error)
        else:
            key = id(observer)
            self._observers[key] = observer
            observer.subscription.add(lambda: self._observers.pop(key, None))

    def on_next(self, value: Any) -> None:
        """Разослать значение текущим подписчикам."""
        for observer in tuple(self._observers.values()):
            try:
                observer.on_next(value)
            except Exception as error:
                observer.on_error(error)

    def on_error(self, error: Exception) -> None:
        """Завершить все активные подписки ошибкой."""
        if not self._done:
            self._done = True
            self._error = error
            for observer in tuple(self._observers.values()):
                observer.on_error(error)

    def on_completed(self) -> None:
        """Нормально завершить все активные подписки."""
        if not self._done:
            self._done = True
            for observer in tuple(self._observers.values()):
                observer.on_completed()
