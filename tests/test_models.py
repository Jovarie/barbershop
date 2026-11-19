"""Tests for the SQL models."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import Appointment, Barber, Service, User


@pytest.fixture
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app


def test_same_slot_cannot_be_booked_twice(app):
    admin = User(email="barber@shop.com", name="Barber", role="admin")
    customer = User(email="c@x.com", name="Customer")
    service = Service(name="Fade", duration_min=30, price_pence=1500)
    db.session.add_all([admin, customer, service])
    db.session.flush()
    barber = Barber(user_id=admin.id)
    db.session.add(barber)
    db.session.flush()
    start = datetime(2026, 12, 1, 10, 0)
    for _ in range(2):
        db.session.add(Appointment(customer_id=customer.id, barber_id=barber.id,
                                   service_id=service.id, starts_at=start,
                                   ends_at=start + timedelta(minutes=30)))
    with pytest.raises(IntegrityError):
        db.session.commit()
