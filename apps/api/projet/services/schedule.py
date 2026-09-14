"""The seven-day programme clock (FR-800).

Every programme runs on the same shape, and that shape is not configurable:
kickoff on a Wednesday, deliverables due by the end of the sixth day, pitches
the following Wednesday. Fixing the weekday is what lets the platform promise a
company rep a specific evening before a single applicant exists, and it is what
lets a participant know on the day they apply exactly which two dates they are
committing to.

Counting runs from kickoff as day zero, so "end of the sixth day" is the Tuesday
night six days later and "the seventh day" is the Wednesday after that.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Monday is 0 in datetime.weekday(), so Wednesday is 2.
KICKOFF_WEEKDAY = 2
KICKOFF_WEEKDAY_NAME = "Wednesday"

SUBMIT_DAY_OFFSET = 6
PITCH_DAY_OFFSET = 7

# Weekdays are a local-calendar idea, not a UTC one: a Wednesday 09:00 kickoff
# in Singapore is a Tuesday in UTC, and validating the UTC weekday would reject
# every correct date.
PROGRAMME_TZ = ZoneInfo("Asia/Singapore")


class ScheduleError(ValueError):
    """A date that would break the seven-day shape."""


@dataclass(frozen=True)
class Schedule:
    """The whole programme clock, derived from one date."""

    kickoff_at: datetime
    submit_deadline_at: datetime
    pitch_at: datetime

    @property
    def local_kickoff(self) -> datetime:
        return self.kickoff_at.astimezone(PROGRAMME_TZ)

    @property
    def local_pitch(self) -> datetime:
        return self.pitch_at.astimezone(PROGRAMME_TZ)


def local_weekday(moment: datetime) -> int:
    """The weekday a human in the programme's timezone would call it."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=PROGRAMME_TZ)
    return moment.astimezone(PROGRAMME_TZ).weekday()


def is_kickoff_day(moment: datetime) -> bool:
    return local_weekday(moment) == KICKOFF_WEEKDAY


def next_kickoff_days(after: datetime, count: int = 8) -> list[datetime]:
    """The next `count` Wednesdays, for the date picker to offer.

    Offering a list beats validating free text: a company never types a date
    that is then rejected.
    """
    local = after.astimezone(PROGRAMME_TZ)
    ahead = (KICKOFF_WEEKDAY - local.weekday()) % 7
    # A Wednesday later today is still too soon to open applications against.
    first = local.date() + timedelta(days=ahead or 7)
    return [
        datetime.combine(first + timedelta(days=7 * i), time(9, 0), tzinfo=PROGRAMME_TZ)
        for i in range(count)
    ]


def derive(kickoff_at: datetime) -> Schedule:
    """Expand a kickoff date into the full clock.

    The deadline lands at 23:59:59 local on the sixth day — "end of the sixth
    day" means the end of it, not the same clock time as kickoff.
    """
    if kickoff_at.tzinfo is None:
        kickoff_at = kickoff_at.replace(tzinfo=PROGRAMME_TZ)
    if not is_kickoff_day(kickoff_at):
        raise ScheduleError(
            f"A programme kicks off on a {KICKOFF_WEEKDAY_NAME}. "
            f"{kickoff_at.astimezone(PROGRAMME_TZ):%A %d %b %Y} is not one."
        )

    local = kickoff_at.astimezone(PROGRAMME_TZ)
    deadline_day = local.date() + timedelta(days=SUBMIT_DAY_OFFSET)
    pitch_day = local.date() + timedelta(days=PITCH_DAY_OFFSET)

    return Schedule(
        kickoff_at=kickoff_at,
        submit_deadline_at=datetime.combine(
            deadline_day, time(23, 59, 59), tzinfo=PROGRAMME_TZ
        ),
        # Pitches run in the evening so working reps and studying participants
        # can both make them; the exact sessions are carved out of this day.
        pitch_at=datetime.combine(pitch_day, time(19, 0), tzinfo=PROGRAMME_TZ),
    )


def validate_applications_close(close_at: datetime | None, kickoff_at: datetime) -> None:
    """Applications must close before kickoff, or seats are sold twice.

    `close_at` typically comes straight off an HTML `datetime-local` input,
    which carries no offset at all — naive by construction, not by mistake.
    `kickoff_at` here is a full Schedule's, already normalised to
    PROGRAMME_TZ by `derive()`. Comparing the two without normalising `close_at`
    the same way raises `TypeError` instead of a clean `ScheduleError`, which is
    exactly the crash this function exists to prevent.
    """
    if close_at is None:
        return
    if close_at.tzinfo is None:
        close_at = close_at.replace(tzinfo=PROGRAMME_TZ)
    if close_at >= kickoff_at:
        raise ScheduleError(
            "Applications must close before kickoff, so offers can go out and "
            "the cohort is known on day one."
        )
