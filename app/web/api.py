"""JSON API and the health check. The order form uses /api/quote to show the
price as the customer chooses."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify, request

from .. import config, pricing, runtime
from ..orders import OrderError
from . import orders

bp = Blueprint("api", __name__)


@bp.get("/api/quote")
def quote():
    args = request.args
    try:
        price = pricing.quote(
            args.get("pickup_city", ""), args.get("delivery_city", ""),
            args.get("size", ""), args.get("service", ""),
        )
    except pricing.PricingError as error:
        return jsonify(error=str(error)), 400
    return jsonify(price.to_dict())


@bp.post("/api/orders")
def place_order():
    try:
        order = orders().place(request.get_json(silent=True) or {})
    except OrderError as error:
        return jsonify(error=str(error)), 400
    return jsonify(order.to_dict()), 201


@bp.get("/api/orders/<code>")
def show_order(code: str):
    order = orders().get(code)
    if order is None:
        abort(404)
    return jsonify(order.to_dict())


# The load balancer calls this to decide whether this container or server
# may receive traffic. It deliberately does not touch the database, so a
# database problem does not make every server look broken at once.
@bp.get("/health")
def health():
    here = runtime.describe()
    return jsonify(status="ok", version=config.APP_VERSION, answered_by=here["id"], zone=here["zone"])
