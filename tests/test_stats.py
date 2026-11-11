from datetime import datetime, timedelta, timezone

from app import stats
from app.orders import OrderService
from app.store import MemoryStore

TODAY = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def make_orders(valid_order):
    clock = {"now": TODAY - timedelta(days=1)}
    service = OrderService(MemoryStore(), clock=lambda: clock["now"])
    old = service.place(valid_order)                                   # yesterday, 12.00
    clock["now"] = TODAY
    service.advance(old.code); service.advance(old.code); service.advance(old.code)   # delivered today
    active = service.place({**valid_order, "recipient_name": "Kofi Annan", "delivery_city": "lagos"})  # 30.00
    cancelled = service.place(valid_order)
    service.cancel(cancelled.code)
    return service.all(), old, active, cancelled


def test_summary(valid_order):
    orders, *_ = make_orders(valid_order)
    summary = stats.summary(orders, TODAY)
    assert summary["total"] == 3
    assert summary["active"] == 1
    assert summary["placed_today"] == 2
    assert summary["delivered_today"] == 1
    assert summary["revenue_cents"] == 1200 + 3000          # the cancelled order is not counted
    assert summary["revenue_today_cents"] == 3000
    assert summary["by_status"] == {"received": 1, "picked_up": 0, "out_for_delivery": 0, "delivered": 1, "cancelled": 1}
    assert summary["by_route"] == {"same_city": 0, "same_country": 2, "cross_border": 1}


def test_summary_of_nothing():
    assert stats.summary([], TODAY)["total"] == 0


def test_search_by_text_and_status(valid_order):
    orders, old, active, cancelled = make_orders(valid_order)
    assert [o.code for o in stats.search(orders, "kofi")] == [active.code]
    assert [o.code for o in stats.search(orders, "LAGOS")] == [active.code]
    assert [o.code for o in stats.search(orders, old.code.lower())] == [old.code]
    assert [o.code for o in stats.search(orders, status="cancelled")] == [cancelled.code]
    assert stats.search(orders, "kofi", "delivered") == []
    assert len(stats.search(orders)) == 3
