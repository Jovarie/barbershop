"""Ask the booking-email cloud function to email the customer.

If EMAIL_FUNCTION_URL isn't set (before the function is deployed) nothing is
sent, and the tests switch it off so they never send real emails.
Email problems never stop a booking going through.
"""
import os

import requests
from flask import current_app


def send_booking_email(kind, appointment):
    """kind is 'booked' or 'cancelled'. Returns True if the function accepted it."""
    url = current_app.config.get("EMAIL_FUNCTION_URL")
    if not url:
        return False
    body = {"kind": kind, "to": appointment.customer.email, "name": appointment.customer.name,
            "service": appointment.service.name,
            "when": appointment.starts_at.strftime("%A %d %B at %H:%M")}
    try:
        response = requests.post(url, json=body, timeout=5,
                                 headers={"X-Function-Secret": os.environ.get("FUNCTION_SECRET", "")})
        if not response.ok:
            current_app.logger.warning("Email function returned %s", response.status_code)
        return response.ok
    except requests.RequestException:
        current_app.logger.warning("Email function could not be reached")
        return False
