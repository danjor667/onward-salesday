"""HTTP layer: the web page, a small JSON API, and the health check."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from . import config, runtime
from .orders import STATUSES, OrderError, OrderStore

bp = Blueprint("orders", __name__)


def store() -> OrderStore:
    return current_app.extensions["orders"]


def render_home(error: str | None = None, status: int = 200):
    page = render_template(
        "index.html",
        owner_name=config.OWNER_NAME,
        lab_name=config.LAB_NAME,
        version=config.APP_VERSION,
        runtime=runtime.describe(),
        orders=store().all(),
        statuses=STATUSES,
        error=error,
    )
    return page, status


# ---- Web page ---------------------------------------------------------------
@bp.get("/")
def home():
    return render_home()


@bp.post("/orders")
def create_order():
    try:
        store().create(
            request.form.get("merchant"),
            request.form.get("customer"),
            request.form.get("destination"),
        )
    except OrderError as error:
        return render_home(error=str(error), status=400)
    return redirect(url_for("orders.home"))


@bp.post("/orders/<int:order_id>/advance")
def advance_order(order_id: int):
    try:
        store().advance(order_id)
    except OrderError as error:
        return render_home(error=str(error), status=400)
    return redirect(url_for("orders.home"))


# ---- JSON API ---------------------------------------------------------------
@bp.get("/api/orders")
def api_list_orders():
    return jsonify([order.to_dict() for order in store().all()])


@bp.post("/api/orders")
def api_create_order():
    data = request.get_json(silent=True) or {}
    try:
        order = store().create(
            data.get("merchant"), data.get("customer"), data.get("destination")
        )
    except OrderError as error:
        return jsonify(error=str(error)), 400
    return jsonify(order.to_dict()), 201


# ---- Health -----------------------------------------------------------------
# The load balancer calls this to decide whether the server may
# receive traffic. A server that fails it is taken out of service and
# replaced by the Auto Scaling group.
@bp.get("/health")
def health():
    return jsonify(status="ok", version=config.APP_VERSION, server=runtime.describe()["server"])
