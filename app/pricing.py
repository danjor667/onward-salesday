"""What a delivery costs and how long it takes.

Price = route base price x parcel size x service level.
All money is held in cents, as whole numbers, so sums never drift.
"""
from __future__ import annotations

from dataclasses import dataclass

CURRENCY = "USD"

# Cities Onward serves, with their country. The route between two cities is
# "same city", "same country" or "cross border".
CITIES = {
    "accra": ("Accra", "Ghana"),
    "kumasi": ("Kumasi", "Ghana"),
    "tema": ("Tema", "Ghana"),
    "lagos": ("Lagos", "Nigeria"),
    "abuja": ("Abuja", "Nigeria"),
    "abidjan": ("Abidjan", "Côte d'Ivoire"),
    "lome": ("Lomé", "Togo"),
    "cotonou": ("Cotonou", "Benin"),
    "dakar": ("Dakar", "Senegal"),
}


@dataclass(frozen=True)
class Route:
    label: str
    base_cents: int
    standard_hours: int
    express_hours: int


ROUTES = {
    "same_city": Route("Same city", 300, standard_hours=24, express_hours=4),
    "same_country": Route("Same country", 800, standard_hours=72, express_hours=24),
    "cross_border": Route("Cross border", 2000, standard_hours=120, express_hours=48),
}

# key: (label, weight limit, price factor in percent)
SIZES = {
    "small": ("Small", "up to 2 kg", 100),
    "medium": ("Medium", "up to 10 kg", 150),
    "large": ("Large", "up to 25 kg", 220),
}

# key: (label, price factor in percent)
SERVICES = {
    "standard": ("Standard", 100),
    "express": ("Express", 150),
}


class PricingError(ValueError):
    """The route, size or service is not one Onward offers."""


@dataclass(frozen=True)
class Quote:
    route_type: str
    base_cents: int
    size_percent: int
    service_percent: int
    total_cents: int
    eta_hours: int

    def to_dict(self) -> dict:
        return {
            "route_type": self.route_type,
            "route_label": ROUTES[self.route_type].label,
            "base_cents": self.base_cents,
            "size_percent": self.size_percent,
            "service_percent": self.service_percent,
            "total_cents": self.total_cents,
            "total": money(self.total_cents),
            "eta_hours": self.eta_hours,
            "eta": duration(self.eta_hours),
            "currency": CURRENCY,
        }


def route_type(pickup_city: str, delivery_city: str) -> str:
    if pickup_city not in CITIES or delivery_city not in CITIES:
        raise PricingError("Please choose a pickup city and a delivery city")
    if pickup_city == delivery_city:
        return "same_city"
    if CITIES[pickup_city][1] == CITIES[delivery_city][1]:
        return "same_country"
    return "cross_border"


def quote(pickup_city: str, delivery_city: str, size: str, service: str) -> Quote:
    kind = route_type(pickup_city, delivery_city)
    if size not in SIZES:
        raise PricingError("Please choose a parcel size")
    if service not in SERVICES:
        raise PricingError("Please choose a delivery speed")
    route = ROUTES[kind]
    size_percent = SIZES[size][2]
    service_percent = SERVICES[service][1]
    return Quote(
        route_type=kind,
        base_cents=route.base_cents,
        size_percent=size_percent,
        service_percent=service_percent,
        total_cents=route.base_cents * size_percent * service_percent // 10_000,
        eta_hours=route.express_hours if service == "express" else route.standard_hours,
    )


def money(cents: int) -> str:
    return f"{CURRENCY} {int(cents) / 100:,.2f}"


def duration(hours: int) -> str:
    if hours < 24:
        return f"within {hours} hours"
    days = hours // 24
    return "within 1 day" if days == 1 else f"within {days} days"
