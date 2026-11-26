"""Application factory: builds and configures the Flask app."""
import os

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from app.extensions import db


def create_app(test_config=None):
    """Create the app. Tests pass test_config to use a throwaway database."""
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    # Cookies only travel over HTTPS unless COOKIE_SECURE=false (for localhost).
    secure = os.environ.get("COOKIE_SECURE", "true").lower() not in {"false", "0", "no"}
    app.config["COOKIE_SECURE"] = secure
    app.config["SESSION_COOKIE_SECURE"] = secure
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    from app import models  # noqa: F401  registers the tables

    from app.auth import security
    app.before_request(security.load_current_user)
    app.before_request(security.check_csrf)
    app.after_request(security.clear_bad_cookie)
    app.jinja_env.globals["csrf_token"] = security.csrf_token

    from app.main.routes import main_bp
    from app.booking.routes import booking_bp
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.reviews.routes import reviews_bp
    from app.api.routes import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    @app.errorhandler(405)
    def not_found(exc):
        """API callers get JSON errors even for URLs that don't exist; website users get HTML."""
        if request.path.startswith("/api/"):
            return jsonify({"error": exc.description}), exc.code
        return exc

    @app.cli.command("init-db")
    def init_db():
        """Create all tables in the database."""
        db.create_all()
        print("Database tables created")

    @app.cli.command("upgrade-db")
    def upgrade_db():
        """One-off Postgres change: cancelled bookings no longer block their slot.

        Swaps the plain unique rule on (barber_id, starts_at) for a partial unique
        index that only covers bookings whose status is 'booked'.
        """
        from sqlalchemy import text
        with db.engine.begin() as conn:  # one transaction: all or nothing
            conn.execute(text("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS no_double_booking"))
            conn.execute(text("DROP INDEX IF EXISTS no_double_booking"))
            conn.execute(text("CREATE UNIQUE INDEX no_double_booking ON appointments "
                              "(barber_id, starts_at) WHERE status = 'booked'"))
        print("Database upgraded: cancelled bookings now free their slot")

    @app.cli.command("demo-past-booking")
    @click.argument("email")
    def demo_past_booking(email):
        """Add a finished appointment for EMAIL so reviews can be tried (and demoed)."""
        from datetime import datetime, timedelta
        from app.models import Appointment, Barber, Service, User
        user = User.query.filter_by(email=email.lower()).first()
        if user is None:
            print("No user with that email. Log in with Google once first.")
            return
        service = Service.query.filter_by(active=True).first()
        start = (datetime.now() - timedelta(days=7)).replace(hour=10, minute=0,
                                                              second=0, microsecond=0)
        db.session.add(Appointment(customer_id=user.id, barber_id=Barber.query.first().id,
                                   service_id=service.id, starts_at=start,
                                   ends_at=start + timedelta(minutes=service.duration_min)))
        db.session.commit()
        print(f"Added a past {service.name} on {start:%d %b} for {user.name}")

    return app
