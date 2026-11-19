from dataclasses import replace
from .model import Cart, Event, Item

def add_item(cart: Cart, event: Event) -> Cart:
    """Сохранить снимок и добавить товар в новую версию."""
    if not event.sku:
        raise ValueError("empty sku")
    if event.price < 0:
        raise ValueError("negative price")
    if event.qty <= 0:
        raise ValueError("invalid quantity")
    existing = next((x for x in cart.items if x.sku == event.sku), None)
    if existing is not None and existing.price != event.price:
        raise ValueError("price mismatch")
    item = Item(event.sku, event.price, event.qty + (existing.qty if existing else 0))
    return replace(cart, items=tuple(sorted((*[x for x in cart.items if x.sku != event.sku],item))))

def remove_item(cart: Cart, event: Event) -> Cart:
    """Удалить количество с проверкой достаточности."""
    if event.qty <= 0:
        raise ValueError("invalid quantity")
    old = next((x for x in cart.items if x.sku == event.sku), None)
    if old is None:
        raise ValueError("unknown sku")
    if event.qty > old.qty:
        raise ValueError("insufficient quantity")
    kept = tuple(x for x in cart.items if x.sku != event.sku)
    items = kept + ((replace(old,qty=old.qty-event.qty),) if event.qty < old.qty else ())
    return replace(cart, items=tuple(sorted(items)))


def reduce_event(cart: Cart, event: Event) -> Cart:
    """Конечный автомат корзины без побочных эффектов."""
    if cart.closed:
        raise ValueError("cart closed")
    if event.op == "add":
        return add_item(cart,event)
    if event.op == "remove":
        return remove_item(cart,event)
    if event.op == "promo":
        if event.code not in ("", "SAVE10", "FIX500"):
            raise ValueError("unknown promo")
        return replace(cart,promo=event.code)
    if event.op == "checkout":
        if not cart.items:
            raise ValueError("empty cart")
        return replace(cart,closed=True)
    raise ValueError("unknown operation")
