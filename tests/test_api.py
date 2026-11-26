"""Tests for the REST API (/api/v1)."""
from app.models import Appointment
from tests.conftest import csrf, login, next_tuesday

SLOT = f"{next_tuesday().isoformat()}T10:00:00"


def api_book(client, slot=SLOT, service_id=1):
    return client.post("/api/v1/bookings", json={"service_id": service_id, "starts_at": slot},
                       headers={"X-CSRF-Token": csrf(client)})


def test_services_are_listed_as_json(client):
    data = client.get("/api/v1/services").get_json()
    assert [s["name"] for s in data["services"]] == ["Haircut"]  # hidden one left out
    assert data["services"][0]["price_pence"] == 1800


def test_free_slots_for_a_day(client):
    data = client.get(f"/api/v1/services/1/slots?date={next_tuesday().isoformat()}").get_json()
    assert SLOT in data["slots"]


def test_bad_date_gives_json_400(client):
    response = client.get("/api/v1/services/1/slots?date=tomorrow")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_unknown_url_gives_json_404(client):
    response = client.get("/api/v1/nothing-here")
    assert response.status_code == 404 and "error" in response.get_json()


def test_bookings_need_login(client):
    assert client.get("/api/v1/bookings").status_code == 401


def test_create_booking_returns_201_with_location(client):
    login(client)
    response = api_book(client)
    assert response.status_code == 201
    assert response.headers["Location"].endswith(f"/api/v1/bookings/{response.get_json()['id']}")
    assert response.get_json()["status"] == "booked"


def test_taken_slot_gives_409(client):
    login(client)
    api_book(client)
    login(client, uid="u2", email="alex@example.com", name="Alex")
    assert api_book(client).status_code == 409
    assert Appointment.query.count() == 1


def test_invalid_booking_body_gives_400(client):
    login(client)
    assert api_book(client, slot="next week").status_code == 400
    assert api_book(client, service_id=2).status_code == 400  # hidden service


def test_post_without_csrf_token_is_rejected(client):
    login(client)
    response = client.post("/api/v1/bookings", json={"service_id": 1, "starts_at": SLOT})
    assert response.status_code == 403
    assert "error" in response.get_json()


def test_list_only_shows_my_bookings(client):
    login(client, uid="u2", email="alex@example.com", name="Alex")
    api_book(client)
    login(client)
    assert client.get("/api/v1/bookings").get_json()["bookings"] == []


def test_cannot_read_someone_elses_booking(client):
    login(client, uid="u2", email="alex@example.com", name="Alex")
    alexs = api_book(client).get_json()["id"]
    login(client)
    assert client.get(f"/api/v1/bookings/{alexs}").status_code == 404


def test_delete_cancels_booking(client):
    login(client)
    booking_id = api_book(client).get_json()["id"]
    response = client.delete(f"/api/v1/bookings/{booking_id}",
                             headers={"X-CSRF-Token": csrf(client)})
    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelled"


def test_delete_without_csrf_token_is_rejected(client):
    login(client)
    booking_id = api_book(client).get_json()["id"]
    assert client.delete(f"/api/v1/bookings/{booking_id}").status_code == 403


def test_reviews_endpoint_works_with_no_reviews(client):
    data = client.get("/api/v1/reviews").get_json()
    assert data == {"summary": None, "reviews": []}


def test_csrf_endpoint_gives_a_token(client):
    assert len(client.get("/api/v1/csrf").get_json()["csrfToken"]) > 20
