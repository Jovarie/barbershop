"""Pages only the barber (admin) can see."""
from datetime import datetime

from flask import Blueprint, render_template

from app.activity import recent_events
from app.auth.security import admin_required
from app.models import Appointment

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def dashboard():
    """Every upcoming booking, soonest first, plus recent activity from MongoDB."""
    upcoming = (Appointment.query
                .filter(Appointment.status == "booked", Appointment.starts_at >= datetime.now())
                .order_by(Appointment.starts_at).all())
    return render_template("admin.html", appointments=upcoming, events=recent_events())
