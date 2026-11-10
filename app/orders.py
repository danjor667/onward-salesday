"""Order logic. No web framework code in here, so it can be tested alone.

Orders are kept in memory, per server. That is enough for this lab, whose
subject is capacity, not storage. A real order system needs a shared database:
see "Limits" in the README.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# An order moves forward through these steps, one at a time.
STATUSES = ("received", "picked_up", "out_for_delivery", "delivered")


class OrderError(ValueError):
    """The request is not a valid order or not a valid status change."""


@dataclass
class Order:
    id: int
    merchant: str
    customer: str
    destination: str
    status: str = STATUSES[0]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def next_status(self) -> str | None:
        position = STATUSES.index(self.status)
        return STATUSES[position + 1] if position + 1 < len(STATUSES) else None

    def to_dict(self) -> dict:
        return asdict(self)


class OrderStore:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    @classmethod
    def with_sample_orders(cls) -> "OrderStore":
        store = cls()
        store.create("Kente Corner", "Ama Mensah", "Accra, Osu")
        store.create("Lagos Gadgets", "Chidi Okafor", "Lagos, Yaba")
        store.advance(1)
        return store

    def create(self, merchant: str, customer: str, destination: str) -> Order:
        values = {
            "merchant": (merchant or "").strip(),
            "customer": (customer or "").strip(),
            "destination": (destination or "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise OrderError(f"Missing: {', '.join(missing)}")
        too_long = [name for name, value in values.items() if len(value) > 100]
        if too_long:
            raise OrderError(f"Too long (100 characters max): {', '.join(too_long)}")
        with self._lock:
            order = Order(id=next(self._ids), **values)
            self._orders[order.id] = order
        return order

    def advance(self, order_id: int) -> Order:
        """Move an order to its next status."""
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise OrderError(f"Order {order_id} not found")
            if order.next_status is None:
                raise OrderError(f"Order {order_id} is already delivered")
            order.status = order.next_status
        return order

    def all(self) -> list[Order]:
        with self._lock:
            return sorted(self._orders.values(), key=lambda o: o.id, reverse=True)
