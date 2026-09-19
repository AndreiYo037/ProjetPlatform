"""Programme dates the company picks (services/schedule.py).

Times of day are fixed: start is 00:00, end is 23:59, in Singapore. The
company chooses which days.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from projet.services import schedule

SGT = ZoneInfo("Asia/Singapore")


def thursday() -> datetime:
    return datetime(2026, 10, 8, 15, 30, tzinfo=SGT)  # a Thursday afternoon


def test_start_is_midnight_on_the_chosen_day():
    start, end, _ = schedule.bind_dates(thursday(), thursday() + timedelta(days=1))
    local = start.astimezone(SGT)
    assert local.date() == datetime(2026, 10, 8, tzinfo=SGT).date()
    assert (local.hour, local.minute) == (0, 0)


def test_end_is_the_last_minute_of_the_chosen_day():
    start, end, _ = schedule.bind_dates(thursday(), thursday() + timedelta(days=1))
    local = end.astimezone(SGT)
    assert local.date() == datetime(2026, 10, 9, tzinfo=SGT).date()
    assert (local.hour, local.minute) == (23, 59)


def test_a_same_day_challenge_is_allowed():
    start, end, _ = schedule.bind_dates(thursday(), thursday())
    assert start.astimezone(SGT).date() == end.astimezone(SGT).date()
    assert end > start


def test_the_challenge_cannot_end_before_it_starts():
    with pytest.raises(schedule.ScheduleError) as error:
        schedule.bind_dates(thursday(), thursday() - timedelta(days=1))
    assert "end before it starts" in str(error.value)


def test_a_naive_date_is_read_as_singapore_not_utc():
    """An HTML date input sends no offset. 8 Oct must stay 8 Oct in SGT."""
    start, _, _ = schedule.bind_dates(datetime(2026, 10, 8, 0, 0), datetime(2026, 10, 9, 0, 0))
    assert start.astimezone(SGT).date() == datetime(2026, 10, 8, tzinfo=SGT).date()


def test_applications_must_close_before_start():
    start, _, _ = schedule.bind_dates(thursday(), thursday() + timedelta(days=1))
    with pytest.raises(schedule.ScheduleError):
        schedule.validate_applications_close(start, start)
    schedule.validate_applications_close(start - timedelta(days=1), start)


def test_no_close_date_is_not_a_schedule_error():
    """A draft may have no closing date yet; publication is what requires start and end."""
    schedule.validate_applications_close(None, thursday())


def test_a_naive_close_date_is_judged_in_singapore_not_rejected_outright():
    start, _, _ = schedule.bind_dates(thursday(), thursday() + timedelta(days=1))
    naive_the_day_before = datetime(2026, 10, 7, 18, 0)
    schedule.validate_applications_close(naive_the_day_before, start)

    naive_after_start = datetime(2026, 10, 8, 10, 0)
    with pytest.raises(schedule.ScheduleError):
        schedule.validate_applications_close(naive_after_start, start)


def test_a_programme_stays_active_until_its_deadline_passes():
    from types import SimpleNamespace

    from projet.models.enums import ProgrammeStatus

    now = datetime(2026, 10, 10, 12, 0, tzinfo=SGT)
    still_running = SimpleNamespace(
        pitch_at=datetime(2026, 10, 14, 23, 59, 59, tzinfo=SGT),
        submit_deadline_at=datetime(2026, 10, 14, 23, 59, 59, tzinfo=SGT),
        status=ProgrammeStatus.COMPLETE,
    )
    assert schedule.programme_is_past(still_running, now) is False

    week_over = SimpleNamespace(
        pitch_at=datetime(2026, 10, 7, 23, 59, 59, tzinfo=SGT),
        submit_deadline_at=datetime(2026, 10, 7, 23, 59, 59, tzinfo=SGT),
        status=ProgrammeStatus.RUNNING,
    )
    assert schedule.programme_is_past(week_over, now) is True

    no_dates_complete = SimpleNamespace(
        pitch_at=None,
        submit_deadline_at=None,
        status=ProgrammeStatus.COMPLETE,
    )
    assert schedule.programme_is_past(no_dates_complete, now) is True
