"""Tests for the booking pages."""
from app.models import Appointment
from tests.conftest import csrf, login, next_tuesday


def book(client, slot):
    return client.post("/book/1", data={"starts_at": slot, "csrf_token": csrf(client)})


def test_services_page_lists_active_services_with_price(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Haircut" in page
    assert "£18.00" in page


def test_services_page_hides_inactive_services(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Old service" not in page


def test_anyone_can_see_free_times(client):
    page = client.get(f"/book/1?date={next_tuesday().isoformat()}").get_data(as_text=True)
    assert "10:00" in page
    assert "Log in to book" in page


def test_booking_needs_login(client):
    response = book(client, f"{next_tuesday().isoformat()}T10:00:00")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert Appointment.query.count() == 0


def test_booking_a_free_slot_saves_it_for_the_logged_in_user(client):
    login(client)
    response = book(client, f"{next_tuesday().isoformat()}T10:00:00")
    assert response.status_code == 302
    appointment = Appointment.query.one()
    assert appointment.customer.email == "sam@example.com"


def test_same_slot_cannot_be_booked_twice(client):
    slot = f"{next_tuesday().isoformat()}T10:00:00"
    login(client)
    book(client, slot)
    login(client, uid="u2", email="alex@example.com", name="Alex")
    book(client, slot)
    assert Appointment.query.count() == 1


def test_booking_without_csrf_token_is_rejected(client):
    login(client)
    response = client.post("/book/1", data={"starts_at": f"{next_tuesday().isoformat()}T10:00:00"})
    assert response.status_code == 403
    assert Appointment.query.count() == 0
