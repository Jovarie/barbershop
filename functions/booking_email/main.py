"""Cloud Run function (lab 8): send a booking email through the Brevo email API.

The Flask app calls this over HTTP after a booking or cancellation, and the
send-reminders function calls it for each reminder. A shared secret in the
X-Function-Secret header stops strangers using it to send emails.
"""
import hmac
import os
import re

import functions_framework
import requests

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

TEMPLATES = {
    "booked": ("You're booked in: {service}, {when}",
               "Hi {name},\n\nYou're booked in for a {service} on {when}.\n\n"
               "Need to change it? You can cancel from My bookings up to 2 hours before.\n\n"
               "See you soon,\nCrown Barbers"),
    "cancelled": ("Booking cancelled: {service}, {when}",
                  "Hi {name},\n\nYour {service} on {when} has been cancelled.\n\n"
                  "We'd love to see you another time.\n\nCrown Barbers"),
    "reminder": ("Reminder: {service} tomorrow at {time}",
                 "Hi {name},\n\nJust a reminder that you're booked in for a {service} "
                 "tomorrow ({when}).\n\nSee you then,\nCrown Barbers"),
}


def build_email(data):
    """Check the request and fill in the template. Returns (email, error)."""
    kind = data.get("kind")
    to = str(data.get("to", ""))
    if kind not in TEMPLATES:
        return None, "kind must be booked, cancelled or reminder"
    if not EMAIL_RE.match(to):
        return None, "to must be an email address"
    fields = {"name": str(data.get("name") or "there")[:100],
              "service": str(data.get("service") or "appointment")[:100],
              "when": str(data.get("when") or "")[:100],
              "time": str(data.get("time") or "")[:20]}
    subject, body = TEMPLATES[kind]
    return {"to": to, "name": fields["name"], "subject": subject.format(**fields),
            "text": body.format(**fields)}, None


@functions_framework.http
def send_booking_email(request):
    """HTTP entry point. Body: {"kind", "to", "name", "service", "when", "time"}."""
    sent_secret = request.headers.get("X-Function-Secret", "")
    if not hmac.compare_digest(sent_secret, os.environ["FUNCTION_SECRET"]):
        return {"error": "forbidden"}, 403

    email, error = build_email(request.get_json(silent=True) or {})
    if error:
        return {"error": error}, 400

    response = requests.post(BREVO_URL, timeout=10, headers={
        "api-key": os.environ["BREVO_API_KEY"], "accept": "application/json"},
        json={"sender": {"name": "Crown Barbers", "email": os.environ["SENDER_EMAIL"]},
              "to": [{"email": email["to"], "name": email["name"]}],
              "subject": email["subject"], "textContent": email["text"]})
    if response.status_code >= 300:
        print("Brevo error", response.status_code, response.text[:300])  # shows in Cloud Logging
        return {"error": "email service failed"}, 502
    return {"sent": True}, 200
