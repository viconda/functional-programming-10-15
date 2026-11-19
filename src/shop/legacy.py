"""Исходная императивная версия магазина, разработанная для исследования."""
import json
from pathlib import Path
from typing import Any


def new_cart() -> dict[str, Any]:
    """Создать изменяемую корзину."""
    cart: dict[str, Any] = {}
    cart["items"] = []
    cart["promo"] = ""
    cart["closed"] = False
    return cart


def check_open(cart: dict[str, Any]) -> None:
    """Отклонить изменение оформленной корзины."""
    if cart["closed"]:
        raise ValueError("cart closed")


def add_item(cart: dict[str, Any], event: dict[str, Any]) -> None:
    """Добавить товар, изменив список строк корзины."""
    check_open(cart)
    sku = str(event.get("sku", "")).strip()
    price = int(event.get("price", 0))
    quantity = int(event.get("qty", 1))
    if not sku:
        raise ValueError("empty sku")
    if price < 0:
        raise ValueError("negative price")
    if quantity <= 0:
        raise ValueError("invalid quantity")
    for item in cart["items"]:
        if item["sku"] == sku:
            if item["price"] != price:
                raise ValueError("price mismatch")
            item["qty"] += quantity
            return
    row = {}
    row["sku"] = sku
    row["price"] = price
    row["qty"] = quantity
    cart["items"].append(row)


def remove_item(cart: dict[str, Any], event: dict[str, Any]) -> None:
    """Удалить количество или всю строку товара."""
    check_open(cart)
    sku = str(event.get("sku", "")).strip()
    quantity = int(event.get("qty", 1))
    if quantity <= 0:
        raise ValueError("invalid quantity")
    for index in range(len(cart["items"])):
        row = cart["items"][index]
        if row["sku"] == sku:
            if quantity > row["qty"]:
                raise ValueError("insufficient quantity")
            row["qty"] -= quantity
            if row["qty"] == 0:
                cart["items"].pop(index)
            return
    raise ValueError("unknown sku")


def set_promo(cart: dict[str, Any], event: dict[str, Any]) -> None:
    """Установить один промокод."""
    check_open(cart)
    code = str(event.get("code", "")).upper().strip()
    if code not in ("", "SAVE10", "FIX500"):
        raise ValueError("unknown promo")
    cart["promo"] = code


def subtotal(cart: dict[str, Any]) -> int:
    """Подсчитать стоимость всех строк в тиынах."""
    total = 0
    for row in cart["items"]:
        total += row["price"] * row["qty"]
    return total


def discount(cart: dict[str, Any]) -> int:
    """Вычислить лучшую из объёмной скидки и промокода."""
    amount = subtotal(cart)
    volume = 0
    promo = 0
    if amount >= 10000:
        volume = amount * 5 // 100
    if cart["promo"] == "SAVE10":
        promo = amount * 10 // 100
    elif cart["promo"] == "FIX500":
        promo = min(500, amount)
    return max(volume, promo)


def delivery(cart: dict[str, Any]) -> int:
    """Доставка бесплатна от 10000 после скидки, пустая корзина стоит ноль."""
    if not cart["items"]:
        return 0
    net = subtotal(cart) - discount(cart)
    if net >= 10000:
        return 0
    return 700


def quote(cart: dict[str, Any]) -> dict[str, Any]:
    """Сформировать снимок цен и строк корзины."""
    result: dict[str, Any] = {}
    result["items"] = []
    for row in sorted(cart["items"], key=lambda item: item["sku"]):
        copied = {}
        copied["sku"] = row["sku"]
        copied["price"] = row["price"]
        copied["qty"] = row["qty"]
        result["items"].append(copied)
    result["subtotal"] = subtotal(cart)
    result["discount"] = discount(cart)
    result["shipping"] = delivery(cart)
    result["total"] = result["subtotal"] - result["discount"] + result["shipping"]
    result["promo"] = cart["promo"]
    result["closed"] = cart["closed"]
    return result


def checkout(cart: dict[str, Any]) -> None:
    """Оформить непустую корзину."""
    check_open(cart)
    if len(cart["items"]) == 0:
        raise ValueError("empty cart")
    cart["closed"] = True


def process(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Выполнить последовательность действий над изменяемой корзиной."""
    cart = new_cart()
    for event in events:
        operation = event.get("op")
        if operation == "add":
            add_item(cart, event)
        elif operation == "remove":
            remove_item(cart, event)
        elif operation == "promo":
            set_promo(cart, event)
        elif operation == "checkout":
            checkout(cart)
        else:
            raise ValueError("unknown operation")
    return quote(cart)


def run_file(source: Path, target: Path) -> None:
    """Прочитать журнал, выполнить расчёт, записать и напечатать результат."""
    text = source.read_text(encoding="utf-8")
    events = json.loads(text)
    result = process(events)
    report = json.dumps(result, ensure_ascii=False, sort_keys=True)
    target.write_text(report, encoding="utf-8")
    print(report)
