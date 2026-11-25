"""Who is logged in, CSRF protection and the @login_required / @admin_required decorators."""
import hmac
import os
import secrets
from functools import wraps

from flask import abort, current_app, g, redirect, request, session, url_for

from app.auth import firebase
from app.extensions import db
from app.models import User

SESSION_COOKIE = "firebase_session"


def admin_emails():
    """Emails listed in ADMIN_EMAILS (comma separated) get the admin role."""
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def user_from_claims(claims):
    """Find the User for a verified Firebase login, creating or linking one if needed."""
    email = (claims.get("email") or "").lower()
    user = User.query.filter_by(google_id=claims["uid"]).first()
    if user is None and email:
        # Link an account that already exists from before login was added.
        user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, name=claims.get("name") or email, role="customer")
        db.session.add(user)
    user.google_id = claims["uid"]
    if email in admin_emails():
        user.role = "admin"
    db.session.commit()
    return user


def load_current_user():
    """Runs before every request: sets g.user from the verified session cookie."""
    g.user = None
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return
    try:
        claims = firebase.verify_session_cookie(cookie)
    except firebase.AuthError:
        g.clear_session_cookie = True  # expired or revoked: remove it
        return
    # The uid is trusted only because Firebase verified the cookie's signature.
    g.user = User.query.filter_by(google_id=claims["uid"]).first()


def clear_bad_cookie(response):
    if g.get("clear_session_cookie"):
        response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def csrf_token():
    """A random token stored in the signed Flask session and echoed back by forms."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    """Runs before every request: reject POSTs that don't carry the right token."""
    if request.method != "POST" or current_app.config.get("CSRF_DISABLED"):
        return
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    saved = session.get("csrf_token", "")
    if not (sent and saved and hmac.compare_digest(sent, saved)):
        abort(403)


def login_required(view):
    """Send visitors who aren't logged in to the login page, then back here."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Only admins (the barber) may see this page."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped
