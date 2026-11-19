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
