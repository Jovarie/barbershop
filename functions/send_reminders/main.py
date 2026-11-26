"""Cloud Run function (lab 8): email tomorrow's customers a reminder.

Cloud Scheduler calls this every evening. It reads tomorrow's bookings from the
Neon (Postgres) database, then asks the booking-email function to send each one.
"""
import hmac
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import functions_framework
import psycopg
import requests

UK = ZoneInfo("Europe/London")

TOMORROW_SQL = """
    SELECT u.email, u.name, s.name, a.starts_at
    FROM appointments a
    JOIN users u ON u.id = a.customer_id
    JOIN services s ON s.id = a.service_id
    WHERE a.status = 'booked' AND a.starts_at >= %s AND a.starts_at < %s
    ORDER BY a.starts_at
"""


def tomorrow_range(now=None):
    """Midnight to midnight tomorrow, UK time (bookings are stored in UK local time)."""
    now = now or datetime.now(UK)
    start = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return start, start + timedelta(days=1)


def reminder_messages(rows):
    """Turn database rows into request bodies for the booking-email function."""
    return [{"kind": "reminder", "to": email, "name": name, "service": service,
             "when": starts_at.strftime("%A %d %B at %H:%M"), "time": starts_at.strftime("%H:%M")}
            for email, name, service, starts_at in rows]


def fetch_tomorrow(database_url):
    # The app's URL says "postgresql+psycopg://" for SQLAlchemy; psycopg wants "postgresql://".
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as conn:
        return conn.execute(TOMORROW_SQL, tomorrow_range()).fetchall()


@functions_framework.http
def send_reminders(request):
    secret = os.environ["FUNCTION_SECRET"]
    if not hmac.compare_digest(request.headers.get("X-Function-Secret", ""), secret):
        return {"error": "forbidden"}, 403

    sent, failed = 0, 0
    for message in reminder_messages(fetch_tomorrow(os.environ["DATABASE_URL"])):
        try:
            r = requests.post(os.environ["EMAIL_FUNCTION_URL"], json=message, timeout=15,
                              headers={"X-Function-Secret": secret})
            sent, failed = (sent + 1, failed) if r.ok else (sent, failed + 1)
        except requests.RequestException:
            failed += 1
    print(f"Reminders sent: {sent}, failed: {failed}")  # shows in Cloud Logging
    return {"sent": sent, "failed": failed}, 200
