"""Booking pages: list services, pick a slot, confirm a booking."""
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.activity import log_event
from app.auth.security import login_required
from app.booking.slots import free_start_times
from app.extensions import db
from app.models import Appointment, Barber, Service, WorkingHours
from app.reviews.routes import reviewed_ids

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/services")
def services():
    """Show every active service with its price and duration."""
    active = Service.query.filter_by(active=True).order_by(Service.price_pence).all()
    return render_template("services.html", services=active)


def _free_slots(barber, service, day):
    """Look up opening hours and existing bookings, then return the free start times."""
    hours = WorkingHours.query.filter_by(barber_id=barber.id, weekday=day.weekday()).first()
    day_start = datetime.combine(day, datetime.min.time())
    booked = Appointment.query.filter(
        Appointment.barber_id == barber.id,
        Appointment.status == "booked",
        Appointment.starts_at >= day_start,
        Appointment.starts_at < day_start + timedelta(days=1),
    ).all()
    busy = [(a.starts_at, a.ends_at) for a in booked]
    return free_start_times(day, hours and hours.start_time, hours and hours.end_time,
                            service.duration_min, busy)


@booking_bp.route("/book/<int:service_id>", methods=["GET", "POST"])
def book(service_id):
    """GET: show free slots for a day. POST: save the chosen slot as a booking."""
    service = db.get_or_404(Service, service_id)
    barber = Barber.query.first()
    if barber is None:
        abort(503)

    if request.method == "POST":
        if g.user is None:  # anyone can browse times, but booking needs a login
            return redirect(url_for("auth.login", next=request.path))
        try:
            starts_at = datetime.fromisoformat(request.form["starts_at"])
        except (KeyError, ValueError):
            abort(400)
        # Re-check the slot is still free: someone may have booked it meanwhile.
        if starts_at not in _free_slots(barber, service, starts_at.date()):
            flash("Sorry, that time has just been taken. Please pick another.")
            return redirect(url_for("booking.book", service_id=service.id,
                                    date=starts_at.date().isoformat()))

        appointment = Appointment(customer_id=g.user.id, barber_id=barber.id,
                                  service_id=service.id, starts_at=starts_at,
                                  ends_at=starts_at + timedelta(minutes=service.duration_min))
        db.session.add(appointment)
        try:
            db.session.commit()
        except IntegrityError:  # the database's no_double_booking constraint fired
            db.session.rollback()
            flash("Sorry, that time has just been taken. Please pick another.")
            return redirect(url_for("booking.book", service_id=service.id,
                                    date=starts_at.date().isoformat()))
        log_event("booking_created", g.user, appointment_id=appointment.id,
                  service=service.name, starts_at=starts_at.isoformat())
        return redirect(url_for("booking.confirmation", appointment_id=appointment.id))

    try:
        day = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        day = date.today()
    slots = _free_slots(barber, service, day)
    return render_template("book.html", service=service, day=day, slots=slots)


@booking_bp.route("/bookings/<int:appointment_id>")
@login_required
def confirmation(appointment_id):
    """Show a booking's details. Only its customer or an admin may see it."""
    appointment = db.get_or_404(Appointment, appointment_id)
    if appointment.customer_id != g.user.id and g.user.role != "admin":
        abort(404)  # 404, not 403, so nobody can tell which booking ids exist
    return render_template("confirmation.html", appointment=appointment)


@booking_bp.route("/my-bookings")
@login_required
def my_bookings():
    """The logged-in customer's own bookings, split into upcoming and past."""
    mine = (Appointment.query.filter_by(customer_id=g.user.id)
            .order_by(Appointment.starts_at.desc()).all())
    now = datetime.now()
    upcoming = sorted((a for a in mine if a.starts_at >= now), key=lambda a: a.starts_at)
    past = [a for a in mine if a.starts_at < now]
    return render_template("my_bookings.html", upcoming=upcoming, past=past,
                           reviewed=reviewed_ids(g.user))
