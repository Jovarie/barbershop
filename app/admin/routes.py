"""Pages only the barber (admin) can see: bookings, services and opening hours."""
import calendar
from datetime import datetime, time

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.activity import log_event, recent_events
from app.auth.security import admin_required
from app.extensions import db
from app.models import Appointment, Barber, Service, WorkingHours

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def dashboard():
    """Every upcoming booking, soonest first, plus recent activity from MongoDB."""
    upcoming = (Appointment.query
                .filter(Appointment.status == "booked", Appointment.starts_at >= datetime.now())
                .order_by(Appointment.starts_at).all())
    return render_template("admin.html", appointments=upcoming, events=recent_events())


# ---------- Services ----------

def _service_from_form(form):
    """Check the service form. Returns (values, errors)."""
    errors = []
    name = form.get("name", "").strip()
    if not 1 <= len(name) <= 100:
        errors.append("Name must be 1 to 100 characters.")
    try:
        duration = int(form.get("duration_min", ""))
        if not 5 <= duration <= 240 or duration % 5:
            raise ValueError
    except ValueError:
        duration = None
        errors.append("Length must be 5 to 240 minutes, in steps of 5.")
    try:
        price_pence = round(float(form.get("price", "")) * 100)
        if not 0 <= price_pence <= 100_000:
            raise ValueError
    except ValueError:
        price_pence = None
        errors.append("Price must be between £0 and £1,000.")
    values = {"name": name, "duration_min": duration, "price_pence": price_pence,
              "active": form.get("active") == "on"}
    return values, errors


@admin_bp.get("/services")
@admin_required
def services():
    """All services, including hidden ones."""
    return render_template("admin_services.html",
                           services=Service.query.order_by(Service.price_pence).all())


@admin_bp.route("/services/new", methods=["GET", "POST"])
@admin_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_service(service_id=None):
    """Add a new service, or change an existing one's name, length, price or visibility."""
    service = db.get_or_404(Service, service_id) if service_id else None
    if request.method == "POST":
        values, errors = _service_from_form(request.form)
        if errors:
            for error in errors:
                flash(error)
            return render_template("admin_service_form.html", service=service,
                                   form=request.form), 400
        if service is None:
            service = Service(**values)
            # The barber offers every service (one-barber shop for now).
            Barber.query.first().services.append(service)
        else:
            for key, value in values.items():
                setattr(service, key, value)
        db.session.commit()
        log_event("service_saved", g.user, service=service.name)
        flash(f"Saved {service.name}.")
        return redirect(url_for("admin.services"))

    form = {}
    if service:
        form = {"name": service.name, "duration_min": service.duration_min,
                "price": f"{service.price_pence / 100:.2f}",
                "active": "on" if service.active else ""}
    else:
        form = {"active": "on"}
    return render_template("admin_service_form.html", service=service, form=form)


# ---------- Opening hours ----------

def _parse_time(value):
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@admin_bp.route("/hours", methods=["GET", "POST"])
@admin_required
def hours():
    """Set which days the shop is open, and from when to when."""
    barber = Barber.query.first()
    if barber is None:
        abort(503)
    existing = {h.weekday: h for h in WorkingHours.query.filter_by(barber_id=barber.id)}

    if request.method == "POST":
        # Check every day first, so a mistake on Friday doesn't half-save the week.
        plan, errors = {}, []
        for weekday in range(7):
            if request.form.get(f"open_{weekday}") != "on":
                plan[weekday] = None
                continue
            start = _parse_time(request.form.get(f"start_{weekday}"))
            end = _parse_time(request.form.get(f"end_{weekday}"))
            if start is None or end is None or start >= end:
                errors.append(f"{calendar.day_name[weekday]}: closing time must be after opening time.")
            plan[weekday] = (start, end)
        if errors:
            for error in errors:
                flash(error)
            return redirect(url_for("admin.hours"))

        for weekday, times in plan.items():
            row = existing.get(weekday)
            if times is None and row:
                db.session.delete(row)
            elif times and row:
                row.start_time, row.end_time = times
            elif times:
                db.session.add(WorkingHours(barber_id=barber.id, weekday=weekday,
                                            start_time=times[0], end_time=times[1]))
        db.session.commit()
        log_event("hours_updated", g.user)
        flash("Opening hours saved. Existing bookings are not changed.")
        return redirect(url_for("admin.hours"))

    days = [{"weekday": d, "name": calendar.day_name[d], "row": existing.get(d)}
            for d in range(7)]
    return render_template("admin_hours.html", days=days)
