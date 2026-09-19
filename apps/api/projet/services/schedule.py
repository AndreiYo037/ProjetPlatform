"""Programme dates the company picks, with fixed times of day.

The company chooses which days a challenge runs. The clock itself is not
configurable: start is midnight on the start date, and the challenge ends at
23:59 on the end date. That is what "24 October" and "25 October" mean, so a
picker never has to ask for a time.
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
# The kickoff Meet is a call on the start date, not the midnight the
# programme becomes active.
KICKOFF_MEETING = time(9, 0)


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


def kickoff_meeting_at(start_at: datetime) -> datetime:
    """When the kickoff call sits on the start date."""
    local = in_programme_tz(start_at)
    return datetime.combine(local.date(), KICKOFF_MEETING, tzinfo=PROGRAMME_TZ)


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
