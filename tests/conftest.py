import os
import re

import pytest

# Tests never run on AWS: do not wait for the EC2 metadata service.
os.environ["ONWARD_SKIP_EC2_METADATA"] = "1"

from app import create_app  # noqa: E402
from app.store import MemoryStore  # noqa: E402

VALID_ORDER = {
    "sender_name": "Kente Corner",
    "pickup_city": "accra",
    "pickup_address": "Makola Market, stall 14",
    "recipient_name": "Esi Boateng",
    "delivery_city": "tema",
    "delivery_address": "Community 1, near the harbour",
    "size": "medium",
    "service": "standard",
    "notes": "",
}


@pytest.fixture
def valid_order():
    return dict(VALID_ORDER)


@pytest.fixture
def app():
    return create_app(MemoryStore(staff_passcode="test-passcode"))


class Browser:
    """A test client that fills in the form token the way a browser would."""

    def __init__(self, client):
        self.client = client
        self.get = client.get

    def token(self, page="/orders/new"):
        html = self.client.get(page).get_data(as_text=True)
        return re.search(r'name="csrf" value="([^"]+)"', html).group(1)

    def post(self, path, data=None, token_from="/orders/new", **kwargs):
        return self.client.post(path, data={**(data or {}), "csrf": self.token(token_from)}, **kwargs)

    def sign_in(self, passcode="test-passcode"):
        return self.post("/ops/login", {"passcode": passcode}, token_from="/ops/login")


@pytest.fixture
def browser(app):
    return Browser(app.test_client())
