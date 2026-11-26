"""Tests for cancelling bookings and the admin services and opening-hours pages."""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Appointment, Service, User, WorkingHours
from tests.conftest import csrf, login, next_tuesday

SLOT = f"{next_tuesday().isoformat()}T10:00:00"


def book(client, slot=SLOT):
    client.post("/book/1", data={"starts_at": slot, "csrf_token": csrf(client)})
    return Appointment.query.order_by(Appointment.id.desc()).first()


def cancel(client, appointment, **extra):
    return client.post(f"/bookings/{appointment.id}/cancel",
                       data={"csrf_token": csrf(client), **extra})


def login_admin(client):
    login(client, uid="b1", email="barber@shop.test", name="Barber")


# ---------- Cancelling ----------

def test_customer_can_cancel_own_booking(client):
    login(client)
    appointment = book(client)
    cancel(client, appointment)
    assert db.session.get(Appointment, appointment.id).status == "cancelled"


def test_cancelled_slot_can_be_booked_again(client):
    login(client)
    cancel(client, book(client))
    login(client, uid="u2", email="alex@example.com", name="Alex")
    rebooked = book(client)
    assert rebooked.status == "booked" and rebooked.customer.name == "Alex"
    assert Appointment.query.count() == 2  # the cancelled one is kept for history


def test_customer_cannot_cancel_someone_elses_booking(client):
    login(client, uid="u2", email="alex@example.com", name="Alex")
    alexs = book(client)
    login(client)  # now Sam
    assert cancel(client, alexs).status_code == 404
    assert db.session.get(Appointment, alexs.id).status == "booked"


def test_customer_cannot_cancel_at_short_notice(client):
    login(client)
    sam = User.query.filter_by(email="sam@example.com").one()
    soon = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    appointment = Appointment(customer_id=sam.id, barber_id=1, service_id=1,
                              starts_at=soon, ends_at=soon + timedelta(minutes=30))
    db.session.add(appointment)
    db.session.commit()
    cancel(client, appointment)
    assert db.session.get(Appointment, appointment.id).status == "booked"


def test_admin_can_cancel_any_booking(client):
    login(client)
    appointment = book(client)
    login_admin(client)
    response = cancel(client, appointment, **{"from": "admin"})
    assert response.headers["Location"].endswith("/admin/")
    assert db.session.get(Appointment, appointment.id).status == "cancelled"


# ---------- Services ----------

def test_customer_cannot_open_admin_services(client):
    login(client)
    assert client.get("/admin/services").status_code == 403


def test_admin_can_add_a_service(client):
    login_admin(client)
    client.post("/admin/services/new", data={"name": "Kids cut", "duration_min": "20",
                                             "price": "12.50", "active": "on",
                                             "csrf_token": csrf(client)})
    kids = Service.query.filter_by(name="Kids cut").one()
    assert kids.price_pence == 1250 and kids.active
    assert "Kids cut" in client.get("/services").get_data(as_text=True)


def test_invalid_service_is_rejected(client):
    login_admin(client)
    response = client.post("/admin/services/new", data={"name": "", "duration_min": "7",
                                                        "price": "-1", "csrf_token": csrf(client)})
    assert response.status_code == 400
    assert Service.query.count() == 2


def test_hidden_service_cannot_be_booked(client):
    login_admin(client)
    client.post("/admin/services/1/edit", data={"name": "Haircut", "duration_min": "30",
                                                "price": "18.00", "csrf_token": csrf(client)})
    assert not db.session.get(Service, 1).active
    assert client.get("/book/1").status_code == 404


# ---------- Opening hours ----------

def test_admin_can_change_opening_hours(client):
    login_admin(client)
    form = {"csrf_token": csrf(client),
            "open_1": "on", "start_1": "10:00", "end_1": "18:00",   # Tuesday, new times
            "open_5": "on", "start_5": "09:00", "end_5": "13:00"}   # Saturday, newly open
    client.post("/admin/hours", data=form)
    hours = {h.weekday: (h.start_time.hour, h.end_time.hour) for h in WorkingHours.query}
    assert hours == {1: (10, 18), 5: (9, 13)}


def test_closing_time_must_be_after_opening(client):
    login_admin(client)
    client.post("/admin/hours", data={"csrf_token": csrf(client),
                                      "open_1": "on", "start_1": "17:00", "end_1": "09:00"})
    tuesday = WorkingHours.query.filter_by(weekday=1).one()
    assert tuesday.start_time.hour == 9  # unchanged
