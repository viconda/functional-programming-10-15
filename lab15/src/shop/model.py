from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Item:
    """Объект-значение товарной строки, деньги в тиынах."""

    sku: str
    price: int
    qty: int


@dataclass(frozen=True)
class Cart:
    """Неизменяемое состояние корзины."""

    items: tuple[Item, ...] = ()
    promo: str = ""
    closed: bool = False


@dataclass(frozen=True)
class Event:
    """Нормализованное действие редьюсера."""

    op: str
    sku: str = ""
    price: int = 0
    qty: int = 1
    code: str = ""
