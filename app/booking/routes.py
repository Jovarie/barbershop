"""Booking pages: list services, pick a slot, confirm a booking."""
from flask import Blueprint, render_template

from app.models import Service

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/services")
def services():
    """Show every active service with its price and duration."""
    active = Service.query.filter_by(active=True).order_by(Service.price_pence).all()
    return render_template("services.html", services=active)
