"""Order logic: what an order is and the rules for placing, moving and
cancelling one. No web or database code in here, so it can be tested alone.

An order is a delivery booking. The sender gets a tracking code and follows
the parcel through its statuses. Where orders are kept is the job of
store.py.
"""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping

from . import pricing

# A parcel moves forward through these steps, one at a time.
STATUSES = ("received", "picked_up", "out_for_delivery", "delivered")
CANCELLED = "cancelled"
ALL_STATUSES = STATUSES + (CANCELLED,)

STATUS_TEXT = {
    "received": ("Order received", "We have your booking and are assigning a rider."),
    "picked_up": ("Picked up", "A rider has collected the parcel."),
    "out_for_delivery": ("Out for delivery", "The parcel is on its way to the recipient."),
    "delivered": ("Delivered", "The parcel has been handed over."),
    "cancelled": ("Cancelled", "This order was cancelled before pickup."),
}

# Text the customer types: field name -> (label, maximum length, required).
TEXT_FIELDS = {
    "sender_name": ("Your name or shop", 80, True),
    "pickup_address": ("Pickup address", 120, True),
    "recipient_name": ("Recipient name", 80, True),
    "delivery_address": ("Delivery address", 120, True),
    "notes": ("Notes for the rider", 200, False),
}

# Letters and digits that are hard to confuse when read aloud or typed.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class OrderError(ValueError):
    """The request is not a valid order or not a valid status change."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalise_code(code: str | None) -> str:
    return (code or "").strip().upper()


@dataclass
class Order:
    code: str
    sender_name: str
    pickup_city: str
    pickup_address: str
    recipient_name: str
    delivery_city: str
    delivery_address: str
    size: str
    service: str
    notes: str
    route_type: str
    price_cents: int
    status: str
    created_at: str   # ISO 8601, UTC
    eta: str          # ISO 8601, UTC
    # When each status was reached, in order: [{"status": ..., "at": ...}]
    history: list[dict] = field(default_factory=list)

    @property
    def next_status(self) -> str | None:
        if self.status not in STATUSES:
            return None
        position = STATUSES.index(self.status)
        return STATUSES[position + 1] if position + 1 < len(STATUSES) else None

    @property
    def can_cancel(self) -> bool:
        """Only before a rider has collected the parcel."""
        return self.status == "received"

    @property
    def is_active(self) -> bool:
        return self.status in STATUSES[:-1]

    @property
    def timeline(self) -> list[dict]:
        """Every step, with the time it was reached (or None if not yet)."""
        reached = {entry["status"]: entry["at"] for entry in self.history}
        steps = [
            {
                "status": status,
                "title": STATUS_TEXT[status][0],
                "detail": STATUS_TEXT[status][1],
                "at": reached.get(status),
                "current": status == self.status,
            }
            for status in STATUSES
        ]
        if self.status == CANCELLED:
            steps = [step for step in steps if step["at"]] + [
                {
                    "status": CANCELLED,
                    "title": STATUS_TEXT[CANCELLED][0],
                    "detail": STATUS_TEXT[CANCELLED][1],
                    "at": reached.get(CANCELLED),
                    "current": True,
                }
            ]
        return steps

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping) -> "Order":
        return cls(**{name: data[name] for name in cls.__dataclass_fields__})


class OrderService:
    """The operations the rest of the application may perform on orders."""

    def __init__(self, store, clock: Callable[[], datetime] = utcnow) -> None:
        self._store = store
        self._clock = clock

    # ---- placing ------------------------------------------------------------
    def place(self, data: Mapping, code: str | None = None) -> Order:
        text = {name: str(data.get(name) or "").strip() for name in TEXT_FIELDS}
        missing = [label for name, (label, _, required) in TEXT_FIELDS.items() if required and not text[name]]
        if missing:
            raise OrderError(f"Please fill in: {', '.join(missing)}")
        too_long = [label for name, (label, limit, _) in TEXT_FIELDS.items() if len(text[name]) > limit]
        if too_long:
            raise OrderError(f"Too long: {', '.join(too_long)}")

        pickup_city = str(data.get("pickup_city") or "")
        delivery_city = str(data.get("delivery_city") or "")
        size = str(data.get("size") or "")
        service = str(data.get("service") or "")
        try:
            price = pricing.quote(pickup_city, delivery_city, size, service)
        except pricing.PricingError as error:
            raise OrderError(str(error)) from error

        now = self._clock()
        order = Order(
            code=code or self._new_code(),
            pickup_city=pickup_city,
            delivery_city=delivery_city,
            size=size,
            service=service,
            route_type=price.route_type,
            price_cents=price.total_cents,
            status=STATUSES[0],
            created_at=now.isoformat(timespec="seconds"),
            eta=(now + timedelta(hours=price.eta_hours)).isoformat(timespec="seconds"),
            history=[{"status": STATUSES[0], "at": now.isoformat(timespec="seconds")}],
            **text,
        )
        # A generated code could, very rarely, already exist: try another.
        while not self._store.create(order.to_dict()):
            if code:
                raise OrderError(f"Order {code} already exists")
            order.code = self._new_code()
        return order

    def seed_samples(self) -> None:
        """Two known orders, so tracking can be tried straight away. Safe to
        call on every start: existing orders are left untouched."""
        samples = [
            ("ONW-DEMO01", dict(sender_name="Kente Corner", pickup_city="accra", pickup_address="Makola Market, stall 14",
                                recipient_name="Ama Mensah", delivery_city="accra", delivery_address="Oxford Street, Osu",
                                size="small", service="express", notes="Call on arrival")),
            ("ONW-DEMO02", dict(sender_name="Lagos Gadgets", pickup_city="lagos", pickup_address="Computer Village, Ikeja",
                                recipient_name="Kwame Boateng", delivery_city="kumasi", delivery_address="Adum, near the post office",
                                size="medium", service="standard", notes="")),
        ]
        for code, data in samples:
            try:
                self.place(data, code=code)
            except OrderError:
                continue  # already there
            if code == "ONW-DEMO01":
                self.advance(code)
                self.advance(code)

    # ---- reading ------------------------------------------------------------
    def get(self, code: str | None) -> Order | None:
        data = self._store.get(normalise_code(code))
        return Order.from_dict(data) if data else None

    def all(self) -> list[Order]:
        """Newest first."""
        orders = [Order.from_dict(data) for data in self._store.all()]
        return sorted(orders, key=lambda order: order.created_at, reverse=True)

    # ---- changing -----------------------------------------------------------
    def advance(self, code: str | None) -> Order:
        """Move a parcel to its next status."""
        order = self._require(code)
        if order.status == CANCELLED:
            raise OrderError(f"{order.code} was cancelled")
        if order.next_status is None:
            raise OrderError(f"{order.code} is already delivered")
        return self._move(order, order.next_status)

    def cancel(self, code: str | None) -> Order:
        order = self._require(code)
        if not order.can_cancel:
            raise OrderError(f"{order.code} can no longer be cancelled: it has been picked up")
        return self._move(order, CANCELLED)

    # ---- helpers ------------------------------------------------------------
    def _require(self, code: str | None) -> Order:
        order = self.get(code)
        if order is None:
            raise OrderError(f"No order with tracking code {normalise_code(code) or '(empty)'}")
        return order

    def _move(self, order: Order, new_status: str) -> Order:
        entry = {"status": new_status, "at": self._clock().isoformat(timespec="seconds")}
        # The store only applies the change if the status is still what we
        # read. This stops two people moving the same parcel twice.
        if not self._store.transition(order.code, order.status, new_status, entry):
            raise OrderError(f"{order.code} was changed by someone else. Refresh and try again.")
        order.status = new_status
        order.history.append(entry)
        return order

    @staticmethod
    def _new_code() -> str:
        return "ONW-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
