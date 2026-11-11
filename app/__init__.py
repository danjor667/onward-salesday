"""Onward Logistics order system: user interface and order logic in one app.

  pricing.py   what a delivery costs
  orders.py    the rules for placing, moving and cancelling orders
  store.py     where orders are kept (memory locally, DynamoDB on AWS)
  stats.py     numbers for the operations dashboard
  security.py  form tokens and the staff passcode
  runtime.py   which container or server is answering
  web/         the pages (customer, operations) and the JSON API
"""
from __future__ import annotations

from datetime import datetime

from flask import Flask

from . import config, pricing, runtime, security
from .orders import STATUS_TEXT, OrderService
from .store import DynamoStore, MemoryStore


def build_store():
    if config.ORDERS_TABLE:
        return DynamoStore.connect(config.ORDERS_TABLE, config.AWS_REGION)
    return MemoryStore(staff_passcode=config.LOCAL_STAFF_PASSCODE)


def create_app(store=None) -> Flask:
    app = Flask(__name__)
    store = store or build_store()

    settings = store.settings()
    app.secret_key = settings["session_key"]
    app.config.update(
        STAFF_PASSCODE=settings["staff_passcode"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=64 * 1024,
    )

    service = OrderService(store)
    service.seed_samples()
    app.extensions["orders"] = service

    from .web import api, customer, ops

    app.register_blueprint(customer.bp)
    app.register_blueprint(ops.bp)
    app.register_blueprint(api.bp)

    # ---- available in every template ----------------------------------------
    @app.context_processor
    def shared_page_values() -> dict:
        return {
            "owner_name": config.OWNER_NAME,
            "lab_name": config.LAB_NAME,
            "version": config.APP_VERSION,
            "runtime": runtime.describe(),
            "csrf_token": security.csrf_token,
            "cities": pricing.CITIES,
            "sizes": pricing.SIZES,
            "services": pricing.SERVICES,
            "routes": pricing.ROUTES,
            "status_text": STATUS_TEXT,
        }

    app.add_template_filter(pricing.money, "money")

    @app.template_filter("when")
    def when(iso: str | None) -> str:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M UTC") if iso else ""

    @app.template_filter("city")
    def city(key: str) -> str:
        return pricing.CITIES[key][0] if key in pricing.CITIES else key

    return app
