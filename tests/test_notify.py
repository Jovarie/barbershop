"""Tests for the Flask side of the email cloud function (app/notify.py)."""
import requests

from tests.conftest import csrf, login, next_tuesday

SLOT = f"{next_tuesday().isoformat()}T10:00:00"


class FakeResponse:
    def __init__(self, ok=True):
        self.ok, self.status_code = ok, 200 if ok else 500


def capture_posts(monkeypatch, app, ok=True, error=None):
    """Point the app at a fake function URL and record what it would send."""
    app.config["EMAIL_FUNCTION_URL"] = "https://email-function.example"
    sent = []

    def fake_post(url, json, timeout, headers):
        if error:
            raise error
        sent.append(json)
        return FakeResponse(ok)
    monkeypatch.setattr(requests, "post", fake_post)
    return sent


def book(client):
    return client.post("/book/1", data={"starts_at": SLOT, "csrf_token": csrf(client)})


def test_booking_sends_confirmation_email(client, app, monkeypatch):
    sent = capture_posts(monkeypatch, app)
    login(client, name="Sam Taylor")
    book(client)
    assert sent[0]["kind"] == "booked"
    assert sent[0]["to"] == "sam@example.com" and sent[0]["service"] == "Haircut"


def test_cancelling_sends_cancellation_email(client, app, monkeypatch):
    sent = capture_posts(monkeypatch, app)
    login(client)
    book(client)
    client.post("/bookings/1/cancel", data={"csrf_token": csrf(client)})
    assert [m["kind"] for m in sent] == ["booked", "cancelled"]


def test_booking_still_works_if_email_function_is_down(client, app, monkeypatch):
    capture_posts(monkeypatch, app, error=requests.ConnectionError())
    login(client)
    response = book(client)
    assert response.status_code == 302 and "/bookings/" in response.headers["Location"]


def test_no_email_when_function_not_configured(client, monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: calls.append(1))
    login(client)
    book(client)
    assert calls == []
