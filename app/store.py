"""Where orders are kept.

Two stores with the same five methods:
  MemoryStore   for local runs and tests. Lost when the process stops.
  DynamoStore   on AWS. One table shared by every server, so an order placed
                on one server is found by all of them and survives restarts.

The store also keeps two application secrets that every server must share:
the staff passcode and the key that signs browser sessions.
"""
from __future__ import annotations

import copy
import secrets
import threading
from decimal import Decimal


def _new_settings(staff_passcode: str | None = None) -> dict:
    return {
        "staff_passcode": staff_passcode or secrets.token_urlsafe(9),
        "session_key": secrets.token_urlsafe(32),
    }


class MemoryStore:
    def __init__(self, staff_passcode: str | None = None) -> None:
        self._orders: dict[str, dict] = {}
        self._settings = _new_settings(staff_passcode)
        self._lock = threading.Lock()

    def create(self, order: dict) -> bool:
        """Save a new order. False if the tracking code is already taken."""
        with self._lock:
            if order["code"] in self._orders:
                return False
            self._orders[order["code"]] = copy.deepcopy(order)
            return True

    def get(self, code: str) -> dict | None:
        with self._lock:
            return copy.deepcopy(self._orders.get(code))

    def transition(self, code: str, from_status: str, to_status: str, entry: dict) -> bool:
        """Change status only if it is still from_status. False otherwise."""
        with self._lock:
            order = self._orders.get(code)
            if order is None or order["status"] != from_status:
                return False
            order["status"] = to_status
            order["history"].append(dict(entry))
            return True

    def all(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(list(self._orders.values()))

    def settings(self) -> dict:
        return dict(self._settings)


class DynamoStore:
    """One DynamoDB table. Each item has a single key, "pk":
         ORDER#<tracking code>   an order
         CONFIG                  the shared application secrets
    """

    def __init__(self, table) -> None:
        self._table = table
        self._conflict = table.meta.client.exceptions.ConditionalCheckFailedException

    @classmethod
    def connect(cls, table_name: str, region: str | None) -> "DynamoStore":
        import boto3  # imported here so local runs do not need AWS at all

        return cls(boto3.resource("dynamodb", region_name=region).Table(table_name))

    def create(self, order: dict) -> bool:
        try:
            self._table.put_item(
                Item={"pk": f"ORDER#{order['code']}", **order},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except self._conflict:
            return False
        return True

    def get(self, code: str) -> dict | None:
        response = self._table.get_item(Key={"pk": f"ORDER#{code}"}, ConsistentRead=True)
        return _plain(response.get("Item"))

    def transition(self, code: str, from_status: str, to_status: str, entry: dict) -> bool:
        try:
            self._table.update_item(
                Key={"pk": f"ORDER#{code}"},
                UpdateExpression="SET #status = :to, #history = list_append(#history, :entry)",
                ConditionExpression="#status = :from",
                ExpressionAttributeNames={"#status": "status", "#history": "history"},
                ExpressionAttributeValues={":to": to_status, ":from": from_status, ":entry": [entry]},
            )
        except self._conflict:
            return False
        return True

    def all(self) -> list[dict]:
        # A scan reads the whole table. Fine for the operations page at this
        # size; a busy system would add an index by status or date.
        items, start_key = [], None
        while True:
            page = self._table.scan(**({"ExclusiveStartKey": start_key} if start_key else {}))
            items += [item for item in page["Items"] if item["pk"].startswith("ORDER#")]
            start_key = page.get("LastEvaluatedKey")
            if not start_key:
                return [_plain(item) for item in items]

    def settings(self) -> dict:
        """The first server to start writes the secrets; every other server
        reads the same ones."""
        try:
            self._table.put_item(
                Item={"pk": "CONFIG", **_new_settings()},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except self._conflict:
            pass
        item = self._table.get_item(Key={"pk": "CONFIG"}, ConsistentRead=True)["Item"]
        return {"staff_passcode": item["staff_passcode"], "session_key": item["session_key"]}


def _plain(item: dict | None) -> dict | None:
    """DynamoDB returns numbers as Decimal and adds our key: undo both."""
    if item is None:
        return None
    return {
        name: int(value) if isinstance(value, Decimal) else value
        for name, value in item.items()
        if name != "pk"
    }
