"""Small security helpers: form tokens and the staff passcode.

Sessions are signed cookies. The signing key is shared by every server (see
store.py), so a session started on one server is accepted by the others.
"""
from __future__ import annotations

import hmac
import secrets
from functools import wraps

from flask import abort, current_app, redirect, request, session, url_for


def csrf_token() -> str:
    """A random value tied to this browser session, put in every form."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(16)
    return session["csrf"]


def check_csrf() -> None:
    """Reject form posts that did not come from one of our own pages."""
    if request.method != "POST":
        return
    sent = request.form.get("csrf", "")
    if not hmac.compare_digest(sent, session.get("csrf", "")) or not sent:
        abort(400, "Your session expired. Go back, refresh the page and try again.")


def passcode_matches(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode(), current_app.config["STAFF_PASSCODE"].encode())


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff"):
            return redirect(url_for("ops.login"))
        return view(*args, **kwargs)

    return wrapped
