"""Tests for reviews and the activity log (both stored in MongoDB)."""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Appointment, User
from app.nosql import get_mongo
from tests.conftest import csrf, login, next_tuesday


def past_appointment(email="sam@example.com", days_ago=3):
    """Create a finished appointment directly in SQL (the booking page only allows future times)."""
    customer = User.query.filter_by(email=email).one()
    start = datetime.now().replace(second=0, microsecond=0) - timedelta(days=days_ago)
    appointment = Appointment(customer_id=customer.id, barber_id=1, service_id=1,
                              starts_at=start, ends_at=start + timedelta(minutes=30))
    db.session.add(appointment)
    db.session.commit()
    return appointment


def review(client, appointment_id, rating="5", comment="Sharp fade"):
    return client.post(f"/reviews/new/{appointment_id}",
                       data={"rating": rating, "comment": comment, "csrf_token": csrf(client)})


def test_customer_can_review_a_past_appointment(client):
    login(client, name="Sam Taylor")
    appointment = past_appointment()
    review(client, appointment.id)
    saved = get_mongo().reviews.find_one({"appointment_id": appointment.id})
    assert saved["rating"] == 5
    assert saved["first_name"] == "Sam"  # surname is not stored for display


def test_cannot_review_a_future_appointment(client):
    login(client)
    client.post("/book/1", data={"starts_at": f"{next_tuesday().isoformat()}T10:00:00",
                                 "csrf_token": csrf(client)})
    future = Appointment.query.one()
    review(client, future.id)
    assert get_mongo().reviews.count_documents({}) == 0


def test_cannot_review_someone_elses_appointment(client):
    login(client, uid="u2", email="alex@example.com", name="Alex")
    alexs = past_appointment(email="alex@example.com")
    login(client)  # now Sam
    assert review(client, alexs.id).status_code == 404


def test_only_one_review_per_appointment(client):
    login(client)
    appointment = past_appointment()
    review(client, appointment.id, rating="5")
    review(client, appointment.id, rating="1")
    assert get_mongo().reviews.count_documents({}) == 1


def test_rating_must_be_one_to_five(client):
    login(client)
    appointment = past_appointment()
    assert review(client, appointment.id, rating="9").status_code == 400
    assert get_mongo().reviews.count_documents({}) == 0


def test_home_page_shows_reviews_and_average(client):
    login(client)
    review(client, past_appointment(days_ago=3).id, rating="5", comment="Best in town")
    review(client, past_appointment(days_ago=10).id, rating="4", comment="")
    page = client.get("/").get_data(as_text=True)
    assert "Best in town" in page
    assert "4.5 out of 5" in page


def test_my_bookings_offers_review_for_past_appointment(client):
    login(client)
    past_appointment()
    assert "Leave a review" in client.get("/my-bookings").get_data(as_text=True)


def test_booking_and_login_are_logged_for_admin(client):
    login(client)
    client.post("/book/1", data={"starts_at": f"{next_tuesday().isoformat()}T10:00:00",
                                 "csrf_token": csrf(client)})
    events = [e["event"] for e in get_mongo().activity_log.find()]
    assert events == ["login", "booking_created"]
    login(client, uid="b1", email="barber@shop.test", name="Barber")
    assert "booking created" in client.get("/admin/").get_data(as_text=True)
