"""Thin wrapper around the Firebase Admin SDK (lab 6).

Everything that talks to Firebase lives here, so tests can swap these two
functions for fakes and run without a network connection or a key file.
"""
import os
import time
from datetime import timedelta

import firebase_admin
from firebase_admin import auth, credentials

SESSION_DURATION = timedelta(days=5)
MAX_LOGIN_AGE_SECONDS = 5 * 60


class AuthError(Exception):
    """The token or cookie could not be trusted."""


def _init():
    """Start the Admin SDK once, using the service account key kept out of git."""
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
        firebase_admin.initialize_app(credentials.Certificate(key_path))


def create_session_cookie(id_token):
    """Check a fresh Google sign-in and swap it for a 5-day session cookie.

    Returns (cookie, claims) where claims holds uid, email and name.
    """
    _init()
    try:
        claims = auth.verify_id_token(id_token, check_revoked=True)
        # Refuse to turn an old sign-in into a new multi-day session.
        if not 0 <= time.time() - claims["auth_time"] < MAX_LOGIN_AGE_SECONDS:
            raise AuthError("Recent sign-in required")
        cookie = auth.create_session_cookie(id_token, expires_in=SESSION_DURATION)
    except (ValueError, KeyError, auth.InvalidIdTokenError, auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError, auth.UserDisabledError) as error:
        raise AuthError(str(error)) from error
    if isinstance(cookie, bytes):
        cookie = cookie.decode("utf-8")
    return cookie, claims


def verify_session_cookie(cookie):
    """Return the claims inside a session cookie, or raise AuthError."""
    _init()
    try:
        return auth.verify_session_cookie(cookie, check_revoked=True)
    except (ValueError, auth.InvalidSessionCookieError, auth.ExpiredSessionCookieError,
            auth.RevokedSessionCookieError, auth.UserDisabledError) as error:
        raise AuthError(str(error)) from error
