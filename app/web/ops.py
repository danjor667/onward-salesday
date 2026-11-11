"""What riders and staff use: a dashboard of all orders, behind a passcode."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, session, url_for

from .. import security, stats
from ..orders import ALL_STATUSES, OrderError, utcnow
from . import orders

bp = Blueprint("ops", __name__, url_prefix="/ops")
bp.before_request(security.check_csrf)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if security.passcode_matches(request.form.get("passcode", "")):
            session["staff"] = True
            return redirect(url_for("ops.dashboard"))
        error = "That passcode is not right."
    return render_template("ops_login.html", error=error), (401 if error else 200)


@bp.post("/logout")
def logout():
    session.pop("staff", None)
    return redirect(url_for("customer.home"))


@bp.get("/")
@security.staff_required
def dashboard(error: str | None = None, status_code: int = 200):
    everything = orders().all()
    text = request.args.get("q", "")
    status = request.args.get("status", "")
    if status not in ALL_STATUSES:
        status = ""
    return render_template(
        "ops.html",
        summary=stats.summary(everything, utcnow()),
        orders=stats.search(everything, text, status),
        q=text, status=status, statuses=ALL_STATUSES, error=error,
    ), status_code


@bp.post("/orders/<code>/advance")
@security.staff_required
def advance(code: str):
    return _change(orders().advance, code)


@bp.post("/orders/<code>/cancel")
@security.staff_required
def cancel(code: str):
    return _change(orders().cancel, code)


def _change(action, code: str):
    try:
        action(code)
    except OrderError as error:
        return dashboard(error=str(error), status_code=400)
    # Keep the search the staff member was looking at.
    return redirect(url_for("ops.dashboard", q=request.form.get("q", ""), status=request.form.get("status", "")))
