"""Tests for the booking pages."""
import pytest

from app import create_app
from app.extensions import db
from app.models import Service


@pytest.fixture
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TESTING": True})
    with app.app_context():
        db.create_all()
        db.session.add_all([
            Service(name="Haircut", duration_min=30, price_pence=1800),
            Service(name="Old service", duration_min=30, price_pence=500, active=False),
        ])
        db.session.commit()
        yield app.test_client()


def test_services_page_lists_active_services_with_price(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Haircut" in page
    assert "£18.00" in page


def test_services_page_hides_inactive_services(client):
    page = client.get("/services").get_data(as_text=True)
    assert "Old service" not in page
