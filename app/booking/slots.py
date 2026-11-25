"""Slot logic: work out which start times are free on a given day.

Kept separate from the routes and the database so it can be unit tested
on its own (pure functions in, list of times out).
"""
from datetime import datetime, timedelta

SLOT_STEP_MIN = 15  # customers can start on the hour, :15, :30 or :45


def free_start_times(day, opens, closes, duration_min, busy, now=None):
    """Return the start times on `day` where a service of `duration_min` fits.

    day: a date. opens/closes: times, or None if the shop is closed.
    busy: list of (start, end) datetimes already booked.
    now: slots before this datetime are hidden (defaults to the real time).
    """
    if opens is None or closes is None:
        return []
    now = now or datetime.now()
    length = timedelta(minutes=duration_min)
    start = datetime.combine(day, opens)
    last_end = datetime.combine(day, closes)
    free = []
    while start + length <= last_end:
        end = start + length
        overlaps = any(b_start < end and b_end > start for b_start, b_end in busy)
        if start > now and not overlaps:
            free.append(start)
        start += timedelta(minutes=SLOT_STEP_MIN)
    return free
