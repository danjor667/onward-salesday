from datetime import datetime, timedelta, timezone

import pytest

from app.orders import CANCELLED, STATUSES, OrderError, OrderService
from app.store import MemoryStore

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def service():
    return OrderService(MemoryStore(), clock=lambda: NOW)


def test_place_gives_code_price_eta_and_first_status(service, valid_order):
    order = service.place(valid_order)
    assert order.code.startswith("ONW-") and len(order.code) == 10
    assert order.route_type == "same_country"
    assert order.price_cents == 1200            # 800 x 1.5 (medium) x 1.0 (standard)
    assert order.status == "received"
    assert datetime.fromisoformat(order.eta) == NOW + timedelta(hours=72)
    assert [entry["status"] for entry in order.history] == ["received"]


def test_placed_order_can_be_read_back_whatever_the_case(service, valid_order):
    order = service.place(valid_order)
    assert service.get(f"  {order.code.lower()} ").to_dict() == order.to_dict()
    assert service.get("ONW-NOPE00") is None
    assert service.get(None) is None


def test_codes_are_unique(service, valid_order):
    assert len({service.place(valid_order).code for _ in range(200)}) == 200


def test_text_is_trimmed_and_notes_are_optional(service, valid_order):
    order = service.place({**valid_order, "sender_name": "  Shop  ", "notes": None})
    assert order.sender_name == "Shop" and order.notes == ""


@pytest.mark.parametrize("name", ["sender_name", "pickup_address", "recipient_name", "delivery_address"])
def test_rejects_missing_text(service, valid_order, name):
    with pytest.raises(OrderError, match="Please fill in"):
        service.place({**valid_order, name: "   "})


def test_rejects_overlong_text(service, valid_order):
    with pytest.raises(OrderError, match="Too long"):
        service.place({**valid_order, "notes": "x" * 201})


@pytest.mark.parametrize(
    "change, message",
    [({"pickup_city": "atlantis"}, "city"), ({"size": "huge"}, "size"), ({"service": ""}, "speed")],
)
def test_rejects_what_onward_does_not_offer(service, valid_order, change, message):
    with pytest.raises(OrderError, match=message):
        service.place({**valid_order, **change})


def test_advance_walks_every_status_then_stops(service, valid_order):
    code = service.place(valid_order).code
    for expected in STATUSES[1:]:
        assert service.advance(code).status == expected
    order = service.get(code)
    assert tuple(entry["status"] for entry in order.history) == STATUSES
    assert order.next_status is None and not order.is_active
    with pytest.raises(OrderError, match="already delivered"):
        service.advance(code)


def test_cancel_only_before_pickup(service, valid_order):
    first = service.place(valid_order).code
    assert service.cancel(first).status == CANCELLED
    with pytest.raises(OrderError, match="cancelled"):
        service.advance(first)

    second = service.place(valid_order).code
    service.advance(second)
    with pytest.raises(OrderError, match="picked up"):
        service.cancel(second)


def test_unknown_order_cannot_be_changed(service):
    for action in (service.advance, service.cancel):
        with pytest.raises(OrderError, match="No order"):
            action("ONW-NOPE00")


def test_timeline_marks_reached_and_current_steps(service, valid_order):
    code = service.place(valid_order).code
    service.advance(code)
    timeline = service.get(code).timeline
    assert [bool(step["at"]) for step in timeline] == [True, True, False, False]
    assert [step["current"] for step in timeline] == [False, True, False, False]


def test_cancelled_timeline_ends_at_cancelled(service, valid_order):
    code = service.place(valid_order).code
    service.cancel(code)
    assert [step["status"] for step in service.get(code).timeline] == ["received", "cancelled"]


def test_a_change_made_elsewhere_is_not_overwritten(valid_order):
    store = MemoryStore()
    service = OrderService(store)
    order = service.place(valid_order)
    # Someone else moves the parcel after we read it.
    store.transition(order.code, "received", "picked_up", {"status": "picked_up", "at": "x"})
    with pytest.raises(OrderError, match="changed by someone else"):
        service._move(order, "cancelled")


def test_samples_are_seeded_once(service):
    service.seed_samples()
    service.seed_samples()
    assert len(service.all()) == 2
    assert service.get("ONW-DEMO01").status == "out_for_delivery"
    assert service.get("ONW-DEMO02").status == "received"


def test_all_lists_newest_first(valid_order):
    times = iter(NOW + timedelta(minutes=i) for i in range(10))
    service = OrderService(MemoryStore(), clock=lambda: next(times))
    first, second = service.place(valid_order), service.place(valid_order)
    assert [order.code for order in service.all()] == [second.code, first.code]
