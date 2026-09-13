"""The seven-day clock (services/schedule.py).

The weekday rule is a product promise, not a formatting preference: a company
rep is told which evening they are pitching before applications open, so the
arithmetic that produces that date is worth pinning down.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from projet.services import schedule

SGT = ZoneInfo("Asia/Singapore")


def wednesday(hour: int = 9) -> datetime:
    return datetime(2026, 10, 7, hour, 0, tzinfo=SGT)  # a Wednesday


def test_kickoff_must_be_a_wednesday():
    thursday = wednesday() + timedelta(days=1)
    with pytest.raises(schedule.ScheduleError) as error:
        schedule.derive(thursday)
    assert "Wednesday" in str(error.value)


def test_deadline_is_the_end_of_the_sixth_day():
    clock = schedule.derive(wednesday())
    local = clock.submit_deadline_at.astimezone(SGT)
    assert local.date() == datetime(2026, 10, 13, tzinfo=SGT).date()  # Tuesday
    assert local.weekday() == 1
    # End of the day means the end of it, not the same clock time as kickoff.
    assert (local.hour, local.minute) == (23, 59)


def test_pitch_lands_on_the_following_wednesday():
    clock = schedule.derive(wednesday())
    local = clock.local_pitch
    assert local.weekday() == schedule.KICKOFF_WEEKDAY
    assert (local - clock.local_kickoff).days == 7


def test_weekday_is_judged_in_singapore_not_utc():
    """Singapore is UTC+8, so an early Wednesday there is still Tuesday in UTC.

    Validating the UTC weekday would reject a correct 7am kickoff.
    """
    utc_equivalent = wednesday(hour=7).astimezone(ZoneInfo("UTC"))
    assert utc_equivalent.weekday() == 1  # Tuesday, in UTC
    assert schedule.is_kickoff_day(utc_equivalent)
    # And it expands to the same clock as any other Wednesday.
    assert schedule.derive(utc_equivalent).local_pitch.weekday() == schedule.KICKOFF_WEEKDAY


def test_offered_days_are_all_wednesdays_in_the_future():
    now = datetime(2026, 10, 7, 15, 0, tzinfo=SGT)  # a Wednesday afternoon
    days = schedule.next_kickoff_days(now, count=4)
    assert len(days) == 4
    assert all(day.astimezone(SGT).weekday() == schedule.KICKOFF_WEEKDAY for day in days)
    # Today is a Wednesday but too late to be one of them.
    assert all(day > now for day in days)
    assert [(b - a).days for a, b in zip(days[:-1], days[1:], strict=True)] == [7, 7, 7]


def test_applications_must_close_before_kickoff():
    clock = schedule.derive(wednesday())
    with pytest.raises(schedule.ScheduleError):
        schedule.validate_applications_close(clock.kickoff_at, clock.kickoff_at)
    # Closing the day before is fine.
    schedule.validate_applications_close(
        clock.kickoff_at - timedelta(days=1), clock.kickoff_at
    )


def test_no_close_date_is_not_a_schedule_error():
    """A draft may have no closing date yet; publication is what requires it."""
    schedule.validate_applications_close(None, wednesday())
