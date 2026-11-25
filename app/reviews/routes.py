"""Customer reviews, stored as documents in MongoDB."""
from datetime import datetime, timezone

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, url_for)
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.activity import log_event
from app.auth.security import login_required
from app.extensions import db
from app.models import Appointment
from app.nosql import get_mongo

reviews_bp = Blueprint("reviews", __name__)
MAX_COMMENT = 500


def latest_reviews(limit=3):
    """The newest reviews, for the home page."""
    try:
        return list(get_mongo().reviews.find().sort("created_at", -1).limit(limit))
    except PyMongoError:
        return []


def rating_summary():
    """Average rating and review count, worked out by a MongoDB aggregation pipeline."""
    pipeline = [{"$group": {"_id": None, "average": {"$avg": "$rating"},
                            "count": {"$sum": 1}}}]
    try:
        result = list(get_mongo().reviews.aggregate(pipeline))
    except PyMongoError:
        return None
    if not result or result[0]["average"] is None:  # no reviews yet
        return None
    return {"average": round(result[0]["average"], 1), "count": result[0]["count"]}


def reviewed_ids(user):
    """Which of this user's appointments already have a review."""
    try:
        docs = get_mongo().reviews.find({"customer_id": user.id}, {"appointment_id": 1})
        return {d["appointment_id"] for d in docs}
    except PyMongoError:
        return set()


@reviews_bp.route("/reviews/new/<int:appointment_id>", methods=["GET", "POST"])
@login_required
def new_review(appointment_id):
    """Let a customer rate one of their own past appointments, once."""
    appointment = db.get_or_404(Appointment, appointment_id)
    if appointment.customer_id != g.user.id:
        abort(404)
    if appointment.starts_at > datetime.now() or appointment.status != "booked":
        flash("You can review an appointment once it has happened.")
        return redirect(url_for("booking.my_bookings"))

    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0
        if not 1 <= rating <= 5 or len(comment) > MAX_COMMENT:
            flash(f"Please choose 1 to 5 stars and keep comments under {MAX_COMMENT} characters.")
            return render_template("review_form.html", appointment=appointment,
                                   comment=comment), 400
        review = {
            "appointment_id": appointment.id,
            "customer_id": g.user.id,
            "first_name": g.user.name.split()[0],  # only the first name is shown publicly
            "service": appointment.service.name,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            get_mongo().reviews.insert_one(review)
        except DuplicateKeyError:  # the unique index on appointment_id fired
            flash("You've already reviewed this appointment.")
            return redirect(url_for("booking.my_bookings"))
        except PyMongoError:
            current_app.logger.exception("Could not save review")
            flash("Sorry, reviews are unavailable right now. Please try again later.")
            return redirect(url_for("booking.my_bookings"))
        log_event("review_posted", g.user, appointment_id=appointment.id, rating=rating)
        flash("Thanks for your review!")
        return redirect(url_for("booking.my_bookings"))

    return render_template("review_form.html", appointment=appointment, comment="")
