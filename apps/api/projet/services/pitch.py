"""Pitch slots: company sets the clock, participants claim first come first served.

Each slot is a JudgingSession with capacity 1. The Google Meet is one room for
the whole block, stored on the programme and copied onto every session.

How many slots exist is how many pieces of work have been handed in — not how
many seats were offered, and not how many people were accepted.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projet.models import JudgingSession, Participant, Programme, Submission, Team, TeamMember
from projet.models.base import utcnow
from projet.services.calendar import ensure_pitch_event
from projet.services.schedule import in_programme_tz, pitch_day_begins_at


class PitchError(ValueError):
    """A schedule or booking that cannot be honoured."""


def listed_sessions(session: Session, programme_id: uuid.UUID) -> list[JudgingSession]:
    return list(
        session.scalars(
            select(JudgingSession)
            .where(JudgingSession.programme_id == programme_id)
            .order_by(JudgingSession.starts_at)
        )
    )


def occupant_map(session: Session, programme_id: uuid.UUID) -> dict[uuid.UUID, Participant]:
    rows = session.scalars(
        select(Participant)
        .where(Participant.programme_id == programme_id)
        .where(Participant.judging_session_id.is_not(None))
        .where(Participant.excluded.is_(False))
    )
    occupied: dict[uuid.UUID, Participant] = {}
    for participant in rows:
        if participant.judging_session_id is not None:
            occupied.setdefault(participant.judging_session_id, participant)
    return occupied


def desired_slot_count(session: Session, programme: Programme) -> int:
    """One slot per handed-in submission, never fewer than already booked."""
    submitted = session.scalar(
        select(func.count(func.distinct(Submission.id)))
        .select_from(Submission)
        .join(Team, Team.id == Submission.team_id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .join(Participant, Participant.id == TeamMember.participant_id)
        .where(Team.programme_id == programme.id)
        .where(Participant.excluded.is_(False))
        .where(Submission.submitted_at.isnot(None))
    ) or 0
    booked = session.scalar(
        select(func.count())
        .select_from(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.judging_session_id.is_not(None))
        .where(Participant.excluded.is_(False))
    ) or 0
    return max(int(submitted), int(booked))


def has_handed_in(session: Session, participant: Participant) -> bool:
    return (
        session.scalar(
            select(Submission.id)
            .join(Team, Team.id == Submission.team_id)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.participant_id == participant.id)
            .where(Submission.submitted_at.isnot(None))
            .limit(1)
        )
        is not None
    )


def is_pickable_grid(programme: Programme) -> bool:
    """Slots exist for participants to claim, rather than auto-assignment."""
    return programme.pitch_starts_at is not None and bool(programme.pitch_duration_minutes)


def refresh_run_order(session: Session, programme_id: uuid.UUID) -> None:
    for index, row in enumerate(listed_sessions(session, programme_id), start=1):
        for participant in session.scalars(
            select(Participant).where(Participant.judging_session_id == row.id)
        ):
            participant.run_order = index


def _stamp_session(row: JudgingSession, programme: Programme) -> None:
    row.capacity = 1
    row.location_or_meet_link = programme.pitch_meet_link
    row.google_event_id = programme.pitch_event_id


def sync_pitch_schedule(
    session: Session,
    programme: Programme,
    *,
    starts_at,
    duration_minutes: int,
) -> list[JudgingSession]:
    if duration_minutes < 1 or duration_minutes > 180:
        raise PitchError("Duration per pitch must be between 1 and 180 minutes.")
    start = in_programme_tz(starts_at)
    programme.pitch_starts_at = start
    programme.pitch_duration_minutes = duration_minutes

    count = desired_slot_count(session, programme)
    step = timedelta(minutes=duration_minutes)
    # The Meet is one room for the block. Keep it at least one slot long so
    # the room exists before the first submission opens a time.
    block_end = start + step * max(count, 1)
    try:
        ensure_pitch_event(session, programme, starts_at=start, ends_at=block_end)
    except Exception:
        # Same posture as kickoff: slots still exist if Calendar is down.
        pass

    existing = listed_sessions(session, programme.id)
    occupants = occupant_map(session, programme.id)
    booked_rows = [row for row in existing if row.id in occupants]
    count = max(count, len(booked_rows))

    kept: list[JudgingSession] = []
    for index in range(count):
        slot_start = start + step * index
        slot_end = slot_start + step
        if index < len(existing):
            row = existing[index]
            row.starts_at = slot_start
            row.ends_at = slot_end
            _stamp_session(row, programme)
            kept.append(row)
        else:
            row = JudgingSession(
                programme_id=programme.id,
                starts_at=slot_start,
                ends_at=slot_end,
                capacity=1,
                location_or_meet_link=programme.pitch_meet_link,
                google_event_id=programme.pitch_event_id,
            )
            session.add(row)
            kept.append(row)

    extras = existing[count:]
    for row in extras:
        if row.id in occupants:
            continue
        session.delete(row)

    session.flush()
    refresh_run_order(session, programme.id)
    return kept


def ensure_free_pitch_slot(session: Session, programme: Programme) -> JudgingSession | None:
    """Resize the grid to one slot per handed-in submission."""
    if not is_pickable_grid(programme):
        return None
    rows = sync_pitch_schedule(
        session,
        programme,
        starts_at=programme.pitch_starts_at,
        duration_minutes=programme.pitch_duration_minutes,
    )
    taken = occupant_map(session, programme.id)
    free = [row for row in rows if row.id not in taken]
    return free[0] if free else None


def pitch_booking_open(programme: Programme) -> bool:
    """Slots can be rearranged until 00:00 SGT on judging day."""
    if programme.pitch_starts_at is None:
        return True
    if programme.pitch_day_emailed_at is not None:
        return False
    return utcnow() < pitch_day_begins_at(programme.pitch_starts_at)


def claim_pitch_slot(
    session: Session, participant: Participant, slot_id: uuid.UUID
) -> JudgingSession:
    if not has_handed_in(session, participant) and participant.judging_session_id is None:
        raise PitchError("Submit your work first, then pick a slot.")
    programme = session.get(Programme, participant.programme_id)
    if (
        participant.judging_session_id is not None
        and programme is not None
        and not pitch_booking_open(programme)
    ):
        raise PitchError("Judging day has started. You cannot change your slot.")
    row = session.execute(
        select(JudgingSession).where(JudgingSession.id == slot_id).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.programme_id != participant.programme_id:
        raise PitchError("That slot is not on this programme.")
    if row.capacity != 1:
        raise PitchError("That session is assigned, not picked.")

    held = session.scalars(
        select(Participant)
        .where(Participant.judging_session_id == row.id)
        .where(Participant.id != participant.id)
        .with_for_update()
    ).first()
    if held is not None:
        raise PitchError("That slot was just taken.")

    participant.judging_session_id = row.id
    session.flush()
    refresh_run_order(session, participant.programme_id)
    return row
