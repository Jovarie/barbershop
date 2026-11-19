"""Application factory: builds and configures the Flask app."""
from flask import Flask


def create_app():
    """Create the Flask app and register its blueprints."""
    app = Flask(__name__)
    from app.main.routes import main_bp
    app.register_blueprint(main_bp)
    return app
