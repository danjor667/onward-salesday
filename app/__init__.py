"""Onward Logistics order system: user interface and order logic in one app."""
from flask import Flask

from .orders import OrderStore
from .routes import bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.extensions["orders"] = OrderStore.with_sample_orders()
    app.register_blueprint(bp)
    return app
