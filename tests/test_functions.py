"""Tests for the two cloud functions in functions/ (run locally, no Google Cloud needed)."""
import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path

import flask
import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent

# functions-framework is only installed in Google Cloud, not in the app's venv.
# Its @functions_framework.http decorator just registers the function, so a
# stand-in that returns the function unchanged is enough for testing.
if "functions_framework" not in sys.modules:
    sys.modules["functions_framework"] = types.SimpleNamespace(http=lambda f: f)


def load(name):
    """Import functions/<name>/main.py under its own name (both files are called main.py)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "functions" / name / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


email_fn = load("booking_email")
reminders_fn = load("send_reminders")


@pytest.fixture
def fake_request():
    """Build a Flask request like Cloud Run functions pass in."""
    app = flask.Flask(__name__)
    contexts = []

    def make(json=None, secret="s3cret"):
        ctx = app.test_request_context(method="POST", json=json or {},
                                       headers={"X-Function-Secret": secret})
        ctx.push()
        contexts.append(ctx)
        return flask.request
    yield make
    for ctx in reversed(contexts):
        ctx.pop()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("FUNCTION_SECRET", "s3cret")
    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv("SENDER_EMAIL", "shop@example.com")


GOOD = {"kind": "booked", "to": "sam@example.com", "name": "Sam", "service": "Haircut",
        "when": "Tuesday 01 December at 10:00"}


def test_email_is_built_from_template():
    email, error = email_fn.build_email(GOOD)
    assert error is None
    assert email["subject"] == "You're booked in: Haircut, Tuesday 01 December at 10:00"
    assert "Hi Sam" in email["text"]


def test_bad_email_address_is_rejected():
    assert email_fn.build_email({**GOOD, "to": "not-an-email"})[1]


def test_unknown_kind_is_rejected():
    assert email_fn.build_email({**GOOD, "kind": "spam"})[1]


def test_wrong_secret_is_forbidden(fake_request, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("must not send"))
    _, status = email_fn.send_booking_email(fake_request(GOOD, secret="guess"))
    assert status == 403


def test_valid_request_calls_brevo(fake_request, monkeypatch):
    calls = []

    class Ok:
        status_code = 201

    def fake_post(url, timeout, headers, json):
        calls.append((url, headers, json))
        return Ok()
    monkeypatch.setattr(requests, "post", fake_post)
    body, status = email_fn.send_booking_email(fake_request(GOOD))
    assert status == 200 and body == {"sent": True}
    url, headers, json = calls[0]
    assert url == email_fn.BREVO_URL and headers["api-key"] == "test-key"
    assert json["to"] == [{"email": "sam@example.com", "name": "Sam"}]


def test_tomorrow_range_is_midnight_to_midnight():
    start, end = reminders_fn.tomorrow_range(datetime(2026, 12, 1, 18, 0))
    assert (start, end) == (datetime(2026, 12, 2), datetime(2026, 12, 3))


def test_reminder_messages_from_rows():
    rows = [("sam@example.com", "Sam", "Haircut", datetime(2026, 12, 2, 10, 30))]
    [message] = reminders_fn.reminder_messages(rows)
    assert message["kind"] == "reminder" and message["time"] == "10:30"
    assert message["when"] == "Wednesday 02 December at 10:30"
