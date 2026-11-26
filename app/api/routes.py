"""REST API (version 1): JSON versions of the booking features.

Reading services, free times and reviews is public. Anything about a user's
own bookings needs the same login session cookie as the website, and changes
(POST, DELETE) also need the CSRF token from GET /api/v1/csrf, sent in the
X-CSRF-Token header. Errors always come back as JSON: {"error": "..."}.
"""
from datetime import date, datetime
from functools import wraps

from flask import Blueprint, g, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

from app.auth.security import csrf_token
from app.booking.routes import SlotTaken, _free_slots, can_cancel, cancel_booking, make_booking
from app.extensions import db
from app.models import Appointment, Barber, Service
from app.reviews.routes import latest_reviews, rating_summary

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


# ---------- helpers ----------

def error(status, message):
    return jsonify({"error": message}), status


@api_bp.errorhandler(HTTPException)
def http_error(exc):
    """Turn every error inside the API (404, 405, ...) into JSON instead of an HTML page."""
    return error(exc.code, exc.description)


def api_login_required(view):
    """Like @login_required, but answers 401 JSON instead of redirecting to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return error(401, "Log in first")
        return view(*args, **kwargs)
    return wrapped


def service_json(service):
    return {"id": service.id, "name": service.name, "duration_min": service.duration_min,
            "price_pence": service.price_pence,
            "slots_url": url_for("api.service_slots", service_id=service.id)}


def booking_json(a):
    return {"id": a.id, "service": a.service.name, "service_id": a.service_id,
            "starts_at": a.starts_at.isoformat(), "ends_at": a.ends_at.isoformat(),
            "status": a.status, "can_cancel": can_cancel(a, g.user),
            "url": url_for("api.get_booking", appointment_id=a.id)}


def _own_booking_or_404(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None or (appointment.customer_id != g.user.id and g.user.role != "admin"):
        return None  # same answer for "doesn't exist" and "not yours"
    return appointment


# ---------- public endpoints ----------

@api_bp.get("/csrf")
def get_csrf():
    """The token to send in the X-CSRF-Token header with POST and DELETE requests."""
    return jsonify({"csrfToken": csrf_token()})


@api_bp.get("/services")
def list_services():
    """Every bookable service, cheapest first."""
    services = Service.query.filter_by(active=True).order_by(Service.price_pence).all()
    return jsonify({"services": [service_json(s) for s in services]})


@api_bp.get("/services/<int:service_id>/slots")
def service_slots(service_id):
    """Free start times for one service on one day: ?date=YYYY-MM-DD (default today)."""
    service = db.session.get(Service, service_id)
    if service is None or not service.active:
        return error(404, "Service not found")
    try:
        day = date.fromisoformat(request.args.get("date") or date.today().isoformat())
    except ValueError:
        return error(400, "date must look like 2026-12-01")
    barber = Barber.query.first()
    slots = _free_slots(barber, service, day) if barber else []
    return jsonify({"service_id": service.id, "date": day.isoformat(),
                    "slots": [s.isoformat() for s in slots]})


@api_bp.get("/reviews")
def list_reviews():
    """Latest reviews and the average rating (from MongoDB)."""
    try:
        limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    except ValueError:
        return error(400, "limit must be a number")
    reviews = [{"first_name": r["first_name"], "service": r["service"], "rating": r["rating"],
                "comment": r["comment"], "created_at": r["created_at"].isoformat()}
               for r in latest_reviews(limit)]
    return jsonify({"summary": rating_summary(), "reviews": reviews})


# ---------- the logged-in user's bookings ----------

@api_bp.get("/bookings")
@api_login_required
def list_bookings():
    """The logged-in user's bookings, newest first."""
    mine = (Appointment.query.filter_by(customer_id=g.user.id)
            .order_by(Appointment.starts_at.desc()).all())
    return jsonify({"bookings": [booking_json(a) for a in mine]})


@api_bp.get("/bookings/<int:appointment_id>")
@api_login_required
def get_booking(appointment_id):
    appointment = _own_booking_or_404(appointment_id)
    if appointment is None:
        return error(404, "Booking not found")
    return jsonify(booking_json(appointment))


@api_bp.post("/bookings")
@api_login_required
def create_booking():
    """Book a time. Body: {"service_id": 1, "starts_at": "2026-12-01T10:00:00"}."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error(400, "Send a JSON body")
    service = db.session.get(Service, data.get("service_id")) \
        if isinstance(data.get("service_id"), int) else None
    if service is None or not service.active:
        return error(400, "service_id must be a bookable service")
    try:
        starts_at = datetime.fromisoformat(str(data.get("starts_at")))
    except ValueError:
        return error(400, "starts_at must look like 2026-12-01T10:00:00")
    try:
        appointment = make_booking(g.user, Barber.query.first(), service, starts_at)
    except SlotTaken:
        return error(409, "That time is not available")
    response = jsonify(booking_json(appointment))
    response.status_code = 201  # Created
    response.headers["Location"] = url_for("api.get_booking", appointment_id=appointment.id)
    return response


@api_bp.delete("/bookings/<int:appointment_id>")
@api_login_required
def delete_booking(appointment_id):
    """Cancel a booking (kept in the database with status 'cancelled')."""
    appointment = _own_booking_or_404(appointment_id)
    if appointment is None:
        return error(404, "Booking not found")
    if not cancel_booking(appointment, g.user):
        return error(409, "This booking can no longer be cancelled")
    return jsonify(booking_json(appointment))
