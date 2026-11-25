"""Tests for the booking pages."""
from datetime import date, time, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Appointment, Barber, Service, User, WorkingHours


def next_tuesday():
    today = date.today()
    return today + timedelta(days=(1 - today.weekday()) % 7 or 7)


@pytest.fixture
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TESTING": True})
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
        yield app.test_client()


def test_services_page_lists_active_services_with_price(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Haircut" in page
    assert "£18.00" in page


def test_services_page_hides_inactive_services(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Old service" not in page


def test_booking_a_free_slot_saves_it(client):
    slot = f"{next_tuesday().isoformat()}T10:00:00"
    response = client.post("/book/1", data={"starts_at": slot, "name": "Sam",
                                            "email": "sam@example.com"})
    assert response.status_code == 302
    assert Appointment.query.count() == 1


def test_same_slot_cannot_be_booked_twice(client):
    slot = f"{next_tuesday().isoformat()}T10:00:00"
    form = {"starts_at": slot, "name": "Sam", "email": "sam@example.com"}
    client.post("/book/1", data=form)
    client.post("/book/1", data={**form, "email": "alex@example.com"})
    assert Appointment.query.count() == 1
