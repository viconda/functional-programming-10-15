from collections.abc import Callable

from .model import Cart


def subtotal(cart: Cart) -> int:
    """Сумма строк корзины."""
    return sum(x.price * x.qty for x in cart.items)


def volume_rule(cart: Cart) -> int:
    """Пять процентов от 10000 тиынов."""
    amount = subtotal(cart)
    return amount * 5 // 100 if amount >= 10000 else 0


def promo_rule(cart: Cart) -> int:
    """Скидка промокода с целочисленным округлением вниз."""
    amount = subtotal(cart)
    return (
        amount * 10 // 100
        if cart.promo == "SAVE10"
        else min(500, amount)
        if cart.promo == "FIX500"
        else 0
    )


def discount(
    cart: Cart, rules: tuple[Callable[[Cart], int], ...] = (volume_rule, promo_rule)
) -> int:
    """Композиция правил, выбирающая наибольшую скидку."""
    return max((rule(cart) for rule in rules), default=0)
