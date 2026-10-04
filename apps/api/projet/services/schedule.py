"""Programme dates the company picks.

Start and end keep the clock the company set. Submissions open at start and
lock at end. Kickoff (online) must be after start. First pitch (online) must
fall after start and before end.
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


def at_programme_moment(moment: datetime) -> datetime:
    """Keep the company's clock, in Singapore time, minutes only."""
    return in_programme_tz(moment).replace(second=0, microsecond=0)


def validate_pitch_window(
    start_at: datetime | None,
    end_at: datetime | None,
    pitch_starts_at: datetime | None,
) -> datetime | None:
    """First pitch must fall after start and before the end deadline."""
    if pitch_starts_at is None:
        return None
    if start_at is None:
        raise ScheduleError("Pick a start date before the first pitch.")
    if end_at is None:
        raise ScheduleError("Pick an end date before the first pitch.")
    pitch = at_programme_moment(pitch_starts_at)
    start = in_programme_tz(start_at)
    end = in_programme_tz(end_at)
    if pitch <= start:
        raise ScheduleError("The first pitch must be after the challenge starts.")
    if pitch >= end:
        raise ScheduleError(
            "The challenge must end after the pitching schedule. "
            "Pick an end time after the first pitch."
        )
    return pitch


def bind_kickoff(
    start_at: datetime | None, kickoff_at: datetime | None
) -> datetime | None:
    """Keep the kickoff call the company picked; it must be after start.

    Kickoff is its own date and time. It is not pinned to the start calendar
    day — only required to fall strictly after submissions open.
    """
    if kickoff_at is None:
        return None
    if start_at is None:
        raise ScheduleError("Pick a start date before the kickoff time.")
    meeting = at_programme_moment(kickoff_at)
    start = in_programme_tz(start_at)
    if meeting <= start:
        raise ScheduleError("Kickoff must be after the challenge starts.")
    return meeting


def pitch_day_begins_at(pitch_starts_at: datetime) -> datetime:
    """00:00 SGT on the calendar day pitching starts."""
    return at_start_of_day(pitch_starts_at)


def bind_dates(
    start_at: datetime | None,
    end_at: datetime | None,
    close_at: datetime | None = None,
) -> tuple[datetime | None, datetime | None, datetime | None]:
    """Keep start/end clocks; pin applications-close to end-of-day."""
    start = at_programme_moment(start_at) if start_at is not None else None
    end = at_programme_moment(end_at) if end_at is not None else None
    close = at_end_of_day(close_at) if close_at is not None else None
    if start is not None and end is not None and end <= start:
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
    stays active. The end clock is the cut; with no dates, only an
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


def submissions_open(programme, now: datetime | None = None) -> bool:
    """Whether participants may upload or hand in work.

    Opens at start_at. With no start clock, stays open until locked by end
    or close-out.
    """
    from projet.models.base import utcnow

    if now is None:
        now = utcnow()
    if programme.start_at is None:
        return True
    return now >= programme.start_at
