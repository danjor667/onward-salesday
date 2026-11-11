"""What customers and merchants use: book a delivery, track it, cancel it."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, session, url_for

from .. import pricing, security
from ..orders import OrderError, normalise_code
from . import orders

bp = Blueprint("customer", __name__)
bp.before_request(security.check_csrf)

RECENT_LIMIT = 5


def _remember(code: str) -> None:
    """Keep this browser's last few tracking codes in its session cookie."""
    recent = [c for c in session.get("recent", []) if c != code]
    session["recent"] = [code, *recent][:RECENT_LIMIT]


def _recent_orders() -> list:
    found = (orders().get(code) for code in session.get("recent", []))
    return [order for order in found if order]


@bp.get("/")
def home():
    return render_template("home.html", recent=_recent_orders())


@bp.get("/orders/new")
def new_order():
    return render_template("order_new.html", form=request.args, error=None)


@bp.post("/orders")
def place_order():
    try:
        order = orders().place(request.form)
    except OrderError as error:
        return render_template("order_new.html", form=request.form, error=str(error)), 400
    _remember(order.code)
    return redirect(url_for("customer.show_order", code=order.code, placed=1))


@bp.get("/track")
def track():
    code = normalise_code(request.args.get("code"))
    if orders().get(code) is None:
        message = f"We could not find an order with tracking code {code}." if code else "Enter a tracking code."
        return render_template("home.html", recent=_recent_orders(), track_error=message), (404 if code else 400)
    return redirect(url_for("customer.show_order", code=code))


@bp.get("/orders/<code>")
def show_order(code: str, error: str | None = None, status: int = 200):
    order = orders().get(code)
    if order is None:
        message = f"We could not find an order with tracking code {normalise_code(code)}."
        return render_template("home.html", recent=_recent_orders(), track_error=message), 404
    price = pricing.quote(order.pickup_city, order.delivery_city, order.size, order.service)
    return render_template(
        "order.html", order=order, price=price, error=error, just_placed="placed" in request.args
    ), status


@bp.post("/orders/<code>/cancel")
def cancel_order(code: str):
    try:
        orders().cancel(code)
    except OrderError as error:
        return show_order(code, error=str(error), status=400)
    return redirect(url_for("customer.show_order", code=normalise_code(code)))
