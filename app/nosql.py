"""MongoDB Atlas connection: the NoSQL half of the app.

SQL (Neon) holds the structured, must-be-consistent data: users, services and
bookings. MongoDB holds flexible, append-heavy documents: reviews and the
activity log. Tests pass a fake client in app.config["MONGO_CLIENT"].
"""
import os

import certifi
from flask import current_app
from pymongo import DESCENDING, MongoClient
from pymongo.errors import ConfigurationError

LOG_RETENTION_SECONDS = 90 * 24 * 60 * 60  # keep activity logs for 90 days


def get_mongo():
    """Return the 'barbershop' database, connecting once per app."""
    if "mongo_db" not in current_app.extensions:
        client = current_app.config.get("MONGO_CLIENT")
        if client is None:
            if not os.environ.get("MONGODB_URI"):
                raise ConfigurationError("MONGODB_URI is not set")
            client = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where(),
                                 serverSelectionTimeoutMS=5000)
        mongo = client["barbershop"]
        # One review per appointment, enforced by the database itself.
        mongo.reviews.create_index("appointment_id", unique=True)
        mongo.reviews.create_index([("created_at", DESCENDING)])
        # TTL index: MongoDB deletes log entries automatically after 90 days.
        mongo.activity_log.create_index("at", expireAfterSeconds=LOG_RETENTION_SECONDS)
        current_app.extensions["mongo_db"] = mongo
    return current_app.extensions["mongo_db"]
