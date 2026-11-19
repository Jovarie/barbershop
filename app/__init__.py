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
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    from app import models  # noqa: F401  registers the tables

    from app.main.routes import main_bp
    app.register_blueprint(main_bp)

    @app.cli.command("init-db")
    def init_db():
        """Create all tables in the database."""
        db.create_all()
        print("Database tables created")

    return app
