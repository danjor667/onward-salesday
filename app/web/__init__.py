"""HTTP layer: customer pages, operations pages and the JSON API."""
from flask import current_app

from ..orders import OrderService


def orders() -> OrderService:
    return current_app.extensions["orders"]
