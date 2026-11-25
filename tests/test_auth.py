"""Tests for login, logout, My bookings and the admin page."""
from app.models import Appointment, User
from tests.conftest import csrf, login, next_tuesday


def book_as(client, hour=10, **user):
    login(client, **user)
    client.post("/book/1", data={"starts_at": f"{next_tuesday().isoformat()}T{hour}:00:00",
                                 "csrf_token": csrf(client)})
    return Appointment.query.order_by(Appointment.id.desc()).first()


def test_login_page_shows_google_button(client):
    assert "Continue with Google" in client.get("/login").get_data(as_text=True)


def test_login_creates_user_and_sets_httponly_cookie(client):
    response = login(client)
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "firebase_session=" in cookie and "HttpOnly" in cookie
    assert User.query.filter_by(google_id="u1").one().email == "sam@example.com"


def test_login_without_csrf_token_is_rejected(client):
    response = client.post("/api/session/login", json={"idToken": "u1|sam@example.com|Sam"})
    assert response.status_code == 403


def test_login_with_bad_token_is_rejected(client):
    response = client.post("/api/session/login", json={"idToken": "bad"},
                           headers={"X-CSRF-Token": csrf(client)})
    assert response.status_code == 401


def test_admin_email_gets_admin_role(client):
    login(client, uid="b1", email="barber@shop.test", name="Barber")
    user = User.query.filter_by(email="barber@shop.test").one()
    assert user.role == "admin" and user.google_id == "b1"  # linked, not duplicated


def test_my_bookings_needs_login(client):
    response = client.get("/my-bookings")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_my_bookings_only_shows_my_own(client):
    book_as(client, hour=10, uid="u2", email="alex@example.com", name="Alex")
    book_as(client, hour=11)  # Sam
    page = client.get("/my-bookings").get_data(as_text=True)
    assert "11:00" in page
    assert "10:00" not in page


def test_cannot_view_someone_elses_booking(client):
    alexs = book_as(client, uid="u2", email="alex@example.com", name="Alex")
    login(client)  # now Sam
    assert client.get(f"/bookings/{alexs.id}").status_code == 404


def test_customer_cannot_open_admin_page(client):
    login(client)
    assert client.get("/admin/").status_code == 403


def test_admin_sees_all_upcoming_bookings(client):
    book_as(client, uid="u2", email="alex@example.com", name="Alex")
    login(client, uid="b1", email="barber@shop.test", name="Barber")
    page = client.get("/admin/").get_data(as_text=True)
    assert "Alex" in page


def test_logout_clears_cookie(client):
    login(client)
    response = client.post("/logout", data={"csrf_token": csrf(client)})
    assert "firebase_session=;" in response.headers["Set-Cookie"]
    assert client.get("/my-bookings").status_code == 302


def test_login_redirect_ignores_other_sites(client):
    page = client.get("/login?next=//evil.example").get_data(as_text=True)
    assert "evil.example" not in page
