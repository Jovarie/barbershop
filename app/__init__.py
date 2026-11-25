"""Application factory: builds and configures the Flask app."""
import os

from dotenv import load_dotenv
from flask import Flask

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
    app.register_blueprint(main_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.cli.command("init-db")
    def init_db():
        """Create all tables in the database."""
        db.create_all()
        print("Database tables created")

    return app
