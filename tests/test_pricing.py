import pytest

from app import pricing


@pytest.mark.parametrize(
    "pickup, delivery, expected",
    [("accra", "accra", "same_city"), ("accra", "kumasi", "same_country"), ("accra", "lagos", "cross_border")],
)
def test_route_type(pickup, delivery, expected):
    assert pricing.route_type(pickup, delivery) == expected


def test_price_is_base_times_size_times_service():
    assert pricing.quote("accra", "accra", "small", "standard").total_cents == 300
    assert pricing.quote("accra", "accra", "medium", "standard").total_cents == 450
    assert pricing.quote("accra", "accra", "medium", "express").total_cents == 675
    assert pricing.quote("accra", "lagos", "large", "express").total_cents == 6600


def test_bigger_further_faster_always_costs_more():
    def total(route, size, service):
        return pricing.quote("accra", route, size, service).total_cents

    assert total("accra", "small", "standard") < total("kumasi", "small", "standard") < total("lagos", "small", "standard")
    assert total("accra", "small", "standard") < total("accra", "medium", "standard") < total("accra", "large", "standard")
    assert total("accra", "small", "standard") < total("accra", "small", "express")


def test_express_is_faster():
    for delivery in ("accra", "kumasi", "lagos"):
        standard = pricing.quote("accra", delivery, "small", "standard").eta_hours
        express = pricing.quote("accra", delivery, "small", "express").eta_hours
        assert express < standard


@pytest.mark.parametrize(
    "args, message",
    [
        (("nowhere", "accra", "small", "standard"), "city"),
        (("accra", "", "small", "standard"), "city"),
        (("accra", "accra", "huge", "standard"), "size"),
        (("accra", "accra", "small", "teleport"), "speed"),
    ],
)
def test_rejects_what_onward_does_not_offer(args, message):
    with pytest.raises(pricing.PricingError, match=message):
        pricing.quote(*args)


def test_money_and_duration_text():
    assert pricing.money(675) == "USD 6.75"
    assert pricing.money(123456) == "USD 1,234.56"
    assert pricing.duration(4) == "within 4 hours"
    assert pricing.duration(24) == "within 1 day"
    assert pricing.duration(120) == "within 5 days"
