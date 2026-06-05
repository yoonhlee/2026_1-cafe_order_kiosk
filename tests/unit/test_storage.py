import pytest

from cafe_order_kiosk.kiosk_store import KioskStore
from cafe_order_kiosk.models import OrderStatus


def test_create_order_and_add_items_total() -> None:
store = KioskStore.with_default_menu()
order = store.create_order(note="hot")

store.add_item(order.id, menu_item_id=1, quantity=2, options=["ice"])
store.add_item(order.id, menu_item_id=2, quantity=1)

order = store.get_order(order.id)
assert order is not None
assert order.total == 3500 * 2 + 4000
assert order.status is OrderStatus.OPEN


def test_remove_item_updates_total() -> None:
store = KioskStore.with_default_menu()
order = store.create_order()

store.add_item(order.id, menu_item_id=1, quantity=1)
store.add_item(order.id, menu_item_id=2, quantity=1)
store.remove_item(order.id, line_index=1)

order = store.get_order(order.id)
assert order is not None
assert order.total == 4000


def test_pay_order_success() -> None:
store = KioskStore.with_default_menu()
order = store.create_order()

store.add_item(order.id, menu_item_id=1, quantity=1)
store.pay_order(order.id, method="card", amount=3500)

order = store.get_order(order.id)
assert order is not None
assert order.status is OrderStatus.PAID
assert order.payment is not None
assert order.payment.method == "card"


def test_pay_order_amount_mismatch() -> None:
store = KioskStore.with_default_menu()
order = store.create_order()

store.add_item(order.id, menu_item_id=1, quantity=1)

with pytest.raises(ValueError, match="Payment amount does not match total"):
store.pay_order(order.id, method="card", amount=1000)


def test_cancel_paid_order_is_error() -> None:
store = KioskStore.with_default_menu()
order = store.create_order()

store.add_item(order.id, menu_item_id=1, quantity=1)
store.pay_order(order.id, method="card", amount=3500)

with pytest.raises(ValueError, match="Paid order cannot be canceled"):
store.cancel_order(order.id)


def test_get_stats_empty() -> None:
    store = KioskStore.with_default_menu()
    stats = store.get_stats()
    assert stats.total_revenue == 0
    assert stats.paid_order_count == 0
    assert stats.top_menus == []


def test_get_stats_excludes_open_and_canceled() -> None:
    store = KioskStore.with_default_menu()

    # PAID order: Americano x2 + Latte x1 = 11,000
    order1 = store.create_order()
    store.add_item(order1.id, menu_item_id=1, quantity=2)
    store.add_item(order1.id, menu_item_id=2, quantity=1)
    store.pay_order(order1.id, method="card", amount=11000)

    # PAID order: Americano x1 = 3,500
    order2 = store.create_order()
    store.add_item(order2.id, menu_item_id=1, quantity=1)
    store.pay_order(order2.id, method="cash", amount=3500)

    # CANCELED — must not be counted
    order3 = store.create_order()
    store.add_item(order3.id, menu_item_id=3, quantity=5)
    store.cancel_order(order3.id)

    # OPEN — must not be counted
    order4 = store.create_order()
    store.add_item(order4.id, menu_item_id=3, quantity=1)

    stats = store.get_stats(top_n=5)
    assert stats.total_revenue == 14500
    assert stats.paid_order_count == 2
    assert len(stats.top_menus) == 2
    # Americano is most popular (qty 3)
    assert stats.top_menus[0].name == "Americano"
    assert stats.top_menus[0].total_quantity == 3
    assert stats.top_menus[0].total_revenue == 10500
    assert stats.top_menus[1].name == "Latte"
    assert stats.top_menus[1].total_quantity == 1


def test_get_stats_top_n_limits_results() -> None:
    store = KioskStore.with_default_menu()

    # Americano=3500, Latte=4000, Cappuccino=4200, Cold Brew=4500,
    # Matcha=4800, Chamomile=3800, Lemonade=4200  => total 29000
    order = store.create_order()
    for menu_id in range(1, 8):
        store.add_item(order.id, menu_item_id=menu_id, quantity=1)
    store.pay_order(order.id, method="card", amount=29000)

    stats = store.get_stats(top_n=3)
    assert len(stats.top_menus) == 3