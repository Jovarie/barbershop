"""Activity log stored in MongoDB (logins, bookings, reviews)."""
from datetime import datetime, timezone

from flask import current_app
from pymongo.errors import PyMongoError

from app.nosql import get_mongo


def log_event(event, user=None, **details):
    """Record something that happened. Never breaks the page if MongoDB is down."""
    entry = {
        "event": event,
        "at": datetime.now(timezone.utc),
        "user_id": user.id if user else None,
        "user_name": user.name if user else None,
        "details": details,
    }
    try:
        get_mongo().activity_log.insert_one(entry)
    except PyMongoError:
        current_app.logger.warning("Could not write activity log entry: %s", event)


def recent_events(limit=20):
    """Newest log entries first, for the admin page."""
    try:
        return list(get_mongo().activity_log.find().sort("at", -1).limit(limit))
    except PyMongoError:
        return []
