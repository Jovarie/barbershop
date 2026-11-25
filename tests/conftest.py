"""Shared test setup: a seeded in-memory database and a fake Firebase.

Tests never talk to the real Firebase. FakeFirebase stands in for the two
functions in app/auth/firebase.py, so a 'token' is just the user's details.
"""
from datetime import date, time, timedelta

import pytest

from app import create_app
from app.auth import firebase
from app.extensions import db
from app.models import Barber, Service, User, WorkingHours


def next_tuesday():
    today = date.today()
    return today + timedelta(days=(1 - today.weekday()) % 7 or 7)


class FakeFirebase:
    """Pretends to be Firebase: the ID token and cookie are 'uid|email|name'."""

    @staticmethod
    def create_session_cookie(id_token):
        if id_token == "bad":
            raise firebase.AuthError("bad token")
        return "cookie:" + id_token, FakeFirebase._claims(id_token)

    @staticmethod
    def verify_session_cookie(cookie):
        if not cookie.startswith("cookie:"):
            raise firebase.AuthError("bad cookie")
        return FakeFirebase._claims(cookie.removeprefix("cookie:"))

    @staticmethod
    def _claims(token):
        uid, email, name = token.split("|")
        return {"uid": uid, "email": email, "name": name}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(firebase, "create_session_cookie", FakeFirebase.create_session_cookie)
    monkeypatch.setattr(firebase, "verify_session_cookie", FakeFirebase.verify_session_cookie)
    monkeypatch.setenv("ADMIN_EMAILS", "barber@shop.test")
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TESTING": True,
                      "COOKIE_SECURE": False})
    with app.app_context():
        db.create_all()
        admin = User(email="barber@shop.test", name="Barber", role="admin")
        db.session.add(admin)
        db.session.flush()
        barber = Barber(user_id=admin.id)
        db.session.add(barber)
        db.session.add_all([
            Service(name="Haircut", duration_min=30, price_pence=1800),
            Service(name="Old service", duration_min=30, price_pence=500, active=False),
        ])
        db.session.flush()
        db.session.add(WorkingHours(barber_id=barber.id, weekday=1,
                                    start_time=time(9, 0), end_time=time(17, 0)))
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client):
    """Put a known CSRF token in the test client's session and return it."""
    with client.session_transaction() as session:
        session["csrf_token"] = "test-token"
    return "test-token"


def login(client, uid="u1", email="sam@example.com", name="Sam"):
    """Log in through the real /api/session/login route using the fake Firebase."""
    return client.post("/api/session/login", json={"idToken": f"{uid}|{email}|{name}"},
                       headers={"X-CSRF-Token": csrf(client)})
