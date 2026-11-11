"""Numbers for the operations dashboard, worked out from the list of orders."""
from __future__ import annotations

from datetime import datetime

from .orders import ALL_STATUSES, CANCELLED, Order
from .pricing import ROUTES


def summary(orders: list[Order], now: datetime) -> dict:
    today = now.date().isoformat()
    billable = [order for order in orders if order.status != CANCELLED]

    def reached_today(order: Order, status: str) -> bool:
        return any(e["status"] == status and e["at"].startswith(today) for e in order.history)

    return {
        "total": len(orders),
        "active": sum(order.is_active for order in orders),
        "placed_today": sum(order.created_at.startswith(today) for order in orders),
        "delivered_today": sum(reached_today(order, "delivered") for order in orders),
        "revenue_cents": sum(order.price_cents for order in billable),
        "revenue_today_cents": sum(order.price_cents for order in billable if order.created_at.startswith(today)),
        "by_status": {status: sum(order.status == status for order in orders) for status in ALL_STATUSES},
        "by_route": {route: sum(order.route_type == route for order in orders) for route in ROUTES},
    }


def search(orders: list[Order], text: str = "", status: str = "") -> list[Order]:
    """Filter by status and by free text (code, names, cities, addresses)."""
    text = text.strip().lower()
    result = []
    for order in orders:
        if status and order.status != status:
            continue
        haystack = " ".join(
            [order.code, order.sender_name, order.recipient_name, order.pickup_city,
             order.delivery_city, order.pickup_address, order.delivery_address]
        ).lower()
        if text and text not in haystack:
            continue
        result.append(order)
    return result
