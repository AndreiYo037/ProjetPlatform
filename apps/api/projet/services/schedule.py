"""Programme dates the company picks, with fixed times of day.

The company chooses which days a challenge runs. Start is midnight on the
start date, and the challenge ends at 23:59 on the end date. Kickoff is the
exception: the company picks a clock time, always on the start date.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

# Dates are a local-calendar idea, not a UTC one: midnight in Singapore is
# still the previous evening in UTC, and pinning the UTC clock would shift
# the day the company thought they had picked.
PROGRAMME_TZ = ZoneInfo("Asia/Singapore")

START_OF_DAY = time(0, 0)
END_OF_DAY = time(23, 59, 59)
KICKOFF_DURATION_HOURS = 1


class ScheduleError(ValueError):
    """Dates that cannot run as a challenge."""


def in_programme_tz(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=PROGRAMME_TZ)
    return moment.astimezone(PROGRAMME_TZ)


def at_start_of_day(moment: datetime) -> datetime:
    """The calendar day the company picked, at 00:00 local."""
    local = in_programme_tz(moment)
    return datetime.combine(local.date(), START_OF_DAY, tzinfo=PROGRAMME_TZ)


def at_end_of_day(moment: datetime) -> datetime:
    """The calendar day the company picked, at 23:59 local."""
    local = in_programme_tz(moment)
    return datetime.combine(local.date(), END_OF_DAY, tzinfo=PROGRAMME_TZ)


def bind_kickoff(
    start_at: datetime | None, kickoff_at: datetime | None
) -> datetime | None:
    """Pin the kickoff call to the start date, using the time the company picked.

    The day is the challenge start; the clock time is theirs. A picker that
    sends a datetime on some other day still lands on the start date.
    """
    if kickoff_at is None:
        return None
    if start_at is None:
        raise ScheduleError("Pick a start date before the kickoff time.")
    day = in_programme_tz(start_at).date()
    clock = in_programme_tz(kickoff_at).time().replace(second=0, microsecond=0)
    return datetime.combine(day, clock, tzinfo=PROGRAMME_TZ)


def pitch_day_begins_at(pitch_starts_at: datetime) -> datetime:
    """00:00 SGT on the calendar day pitching starts."""
    return at_start_of_day(pitch_starts_at)


def bind_dates(
    start_at: datetime | None,
    end_at: datetime | None,
    close_at: datetime | None = None,
) -> tuple[datetime | None, datetime | None, datetime | None]:
    """Pin chosen days to the fixed times and refuse an inverted clock."""
    start = at_start_of_day(start_at) if start_at is not None else None
    end = at_end_of_day(end_at) if end_at is not None else None
    close = at_end_of_day(close_at) if close_at is not None else None
    if start is not None and end is not None and end.date() < start.date():
        raise ScheduleError("The challenge cannot end before it starts.")
    if start is not None:
        validate_applications_close(close, start)
    return start, end, close


def validate_applications_close(close_at: datetime | None, start_at: datetime) -> None:
    """Applications must close before the challenge starts, or seats are sold twice.

    `close_at` typically comes straight off an HTML date input, which carries
    no offset at all — naive by construction, not by mistake. Comparing the
    two without normalising `close_at` the same way raises TypeError instead
    of a clean ScheduleError.
    """
    if close_at is None:
        return
    close_at = in_programme_tz(close_at)
    start_at = in_programme_tz(start_at)
    if close_at >= start_at:
        raise ScheduleError(
            "Applications must close before the challenge starts, so offers "
            "can go out and the cohort is known on day one."
        )


def format_sgt_date(moment: datetime | None) -> str | None:
    """Calendar day in Singapore: Sunday 27 September SGT."""
    if moment is None:
        return None
    local = in_programme_tz(moment)
    return f"{local.strftime(f'%A {local.day} %B')} SGT"


def format_sgt_day(moment: datetime | None) -> str | None:
    """Shorter calendar day: 27 September SGT."""
    if moment is None:
        return None
    local = in_programme_tz(moment)
    return f"{local.strftime(f'{local.day} %B')} SGT"


def format_sgt_datetime(moment: datetime | None) -> str | None:
    """Date, clock, and region. Always Singapore time."""
    if moment is None:
        return None
    local = in_programme_tz(moment)
    return f"{local.strftime(f'%A {local.day} %B, %H:%M')} SGT"


def programme_is_past(programme, now: datetime | None = None) -> bool:
    """Whether the challenge is over.

    Active vs past is a calendar question, not a status one: a company can run
    several programmes at once, and a closed-out row whose end is still ahead
    stays active. The end of the last day is the cut; with no dates, only an
    already-complete row is past.
    """
    from projet.models.base import utcnow
    from projet.models.enums import ProgrammeStatus

    if now is None:
        now = utcnow()
    end = programme.submit_deadline_at or programme.pitch_at
    if end is not None:
        return end <= now
    return programme.status == ProgrammeStatus.COMPLETE
