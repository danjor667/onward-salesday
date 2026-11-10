import pytest

from app.orders import STATUSES, OrderError, OrderStore


def test_create_assigns_ids_and_starts_as_received():
    store = OrderStore()
    first = store.create("Shop", "Ama", "Accra")
    second = store.create("Shop", "Kofi", "Kumasi")
    assert (first.id, second.id) == (1, 2)
    assert first.status == "received"


def test_create_trims_whitespace():
    order = OrderStore().create("  Shop ", " Ama ", " Accra ")
    assert (order.merchant, order.customer, order.destination) == ("Shop", "Ama", "Accra")


@pytest.mark.parametrize("fields", [("", "Ama", "Accra"), ("Shop", "  ", "Accra"), ("Shop", "Ama", None)])
def test_create_rejects_missing_fields(fields):
    with pytest.raises(OrderError, match="Missing"):
        OrderStore().create(*fields)


def test_create_rejects_overlong_fields():
    with pytest.raises(OrderError, match="Too long"):
        OrderStore().create("x" * 101, "Ama", "Accra")


def test_advance_walks_through_every_status_then_stops():
    store = OrderStore()
    order = store.create("Shop", "Ama", "Accra")
    seen = [order.status]
    for _ in STATUSES[1:]:
        seen.append(store.advance(order.id).status)
    assert tuple(seen) == STATUSES
    with pytest.raises(OrderError, match="already delivered"):
        store.advance(order.id)


def test_advance_unknown_order():
    with pytest.raises(OrderError, match="not found"):
        OrderStore().advance(99)


def test_all_lists_newest_first():
    store = OrderStore()
    store.create("Shop", "Ama", "Accra")
    store.create("Shop", "Kofi", "Kumasi")
    assert [order.id for order in store.all()] == [2, 1]
