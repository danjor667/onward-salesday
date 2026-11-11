"""The same checks run against both stores, so they stay interchangeable.
DynamoDB is simulated in memory by moto: no AWS account is touched."""
import boto3
import pytest
from moto import mock_aws

from app.orders import OrderService
from app.store import DynamoStore, MemoryStore


@pytest.fixture(params=["memory", "dynamodb"])
def store(request, monkeypatch):
    if request.param == "memory":
        yield MemoryStore()
        return
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(name, "testing")
    with mock_aws():
        boto3.client("dynamodb", region_name="eu-central-1").create_table(
            TableName="orders",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield DynamoStore.connect("orders", "eu-central-1")


def test_create_then_get_returns_the_same_order(store, valid_order):
    order = OrderService(store).place(valid_order)
    assert store.get(order.code) == order.to_dict()
    assert isinstance(store.get(order.code)["price_cents"], int)
    assert store.get("ONW-NOPE00") is None


def test_create_refuses_a_code_that_is_taken(store, valid_order):
    order = OrderService(store).place(valid_order).to_dict()
    assert store.create(order) is False


def test_transition_only_from_the_expected_status(store, valid_order):
    code = OrderService(store).place(valid_order).code
    entry = {"status": "picked_up", "at": "2026-11-11T09:00:00+00:00"}
    assert store.transition(code, "received", "picked_up", entry) is True
    assert store.transition(code, "received", "cancelled", entry) is False   # no longer "received"
    assert store.transition("ONW-NOPE00", "received", "picked_up", entry) is False
    saved = store.get(code)
    assert saved["status"] == "picked_up"
    assert [e["status"] for e in saved["history"]] == ["received", "picked_up"]


def test_all_returns_orders_only(store, valid_order):
    service = OrderService(store)
    codes = {service.place(valid_order).code for _ in range(3)}
    store.settings()   # the settings item must not appear among the orders
    assert {order["code"] for order in store.all()} == codes


def test_settings_are_created_once_and_then_shared(store):
    first, second = store.settings(), store.settings()
    assert first == second
    assert len(first["staff_passcode"]) >= 10 and len(first["session_key"]) >= 32


def test_whole_service_works_on_either_store(store, valid_order):
    service = OrderService(store)
    service.seed_samples()
    code = service.place(valid_order).code
    service.advance(code)
    assert service.get(code).status == "picked_up"
    assert len(service.all()) == 3
