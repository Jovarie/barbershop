"""Unit tests for the slot logic (no database needed)."""
from datetime import date, datetime, time

from app.booking.slots import free_start_times

TUESDAY = date(2026, 12, 1)
BEFORE = datetime(2026, 11, 1)  # "now" is earlier, so no slots count as past


def test_closed_day_has_no_slots():
    assert free_start_times(TUESDAY, None, None, 30, [], now=BEFORE) == []


def test_slots_stay_inside_opening_hours():
    slots = free_start_times(TUESDAY, time(9, 0), time(10, 0), 30, [], now=BEFORE)
    assert [s.time() for s in slots] == [time(9, 0), time(9, 15), time(9, 30)]


def test_booked_time_and_overlaps_are_hidden():
    busy = [(datetime(2026, 12, 1, 9, 30), datetime(2026, 12, 1, 10, 0))]
    slots = free_start_times(TUESDAY, time(9, 0), time(11, 0), 30, busy, now=BEFORE)
    times = [s.time() for s in slots]
    assert time(9, 30) not in times
    assert time(9, 15) not in times  # 9:15-9:45 would overlap the booking
    assert time(9, 0) in times and time(10, 0) in times


def test_past_times_are_hidden():
    now = datetime(2026, 12, 1, 9, 20)
    slots = free_start_times(TUESDAY, time(9, 0), time(10, 0), 15, [], now=now)
    assert [s.time() for s in slots] == [time(9, 30), time(9, 45)]
