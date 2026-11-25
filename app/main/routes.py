"""Public pages of the barbershop site."""
from flask import Blueprint, render_template

from app.reviews.routes import latest_reviews, rating_summary

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Show the home page with the latest customer reviews from MongoDB."""
    return render_template("index.html", reviews=latest_reviews(), summary=rating_summary())
