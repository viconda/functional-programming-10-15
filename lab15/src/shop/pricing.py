from dataclasses import asdict
from typing import Any

from .discounts import discount, subtotal
from .model import Cart


def quote(cart: Cart) -> dict[str, Any]:
    """Вернуть совместимый отчёт с новыми контейнерами."""
    amount, saved = subtotal(cart), discount(cart)
    shipping = 700 if cart.items and amount - saved < 10000 else 0
    return {
        "items": [asdict(x) for x in cart.items],
        "subtotal": amount,
        "discount": saved,
        "shipping": shipping,
        "total": amount - saved + shipping,
        "promo": cart.promo,
        "closed": cart.closed,
    }
