"""Login and logout with Firebase Google Sign-In (based on lab 6)."""
import os

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from app.auth import firebase
from app.auth.security import SESSION_COOKIE, user_from_claims

auth_bp = Blueprint("auth", __name__)


def _safe_next(target):
    """Only allow redirects to pages on this site (stops open-redirect tricks)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("booking.my_bookings")


@auth_bp.get("/login")
def login():
    """The page with the 'Continue with Google' button."""
    firebase_config = {
        "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
        "appId": os.environ.get("FIREBASE_APP_ID", ""),
    }
    return render_template("login.html", firebase_config=firebase_config,
                           next_url=_safe_next(request.args.get("next")))


@auth_bp.post("/api/session/login")
def session_login():
    """Swap a Google ID token from the browser for an HttpOnly session cookie."""
    payload = request.get_json(silent=True) or {}
    id_token = payload.get("idToken")
    if not isinstance(id_token, str) or not id_token:
        return jsonify({"error": "Missing Firebase ID token"}), 400
    try:
        cookie, claims = firebase.create_session_cookie(id_token)
    except firebase.AuthError:
        return jsonify({"error": "Invalid or expired sign-in, please try again"}), 401

    user = user_from_claims(claims)
    response = jsonify({"message": "Logged in", "name": user.name})
    response.set_cookie(SESSION_COOKIE, cookie,
                        max_age=int(firebase.SESSION_DURATION.total_seconds()),
                        httponly=True, secure=current_app.config["COOKIE_SECURE"],
                        samesite="Lax", path="/")
    return response


@auth_bp.post("/logout")
def logout():
    """Remove this browser's session cookie."""
    response = redirect(url_for("main.index"))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
