"""Calendar event creation for programme milestones.

Kickoff and pitching Meets are created when those dates are set. Participants
are not added as attendees — they get the Meet link in email and on the
dashboard.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from projet.integrations.google.client import EventSpec, get_google_client
from projet.models import Company, Programme
from projet.services.schedule import KICKOFF_DURATION_HOURS, bind_kickoff


def ensure_kickoff_event(session: Session, programme: Programme) -> str | None:
    """Create the kickoff Calendar event if it doesn't exist yet.

    Returns the event_id, or None if the kickoff time has not been picked.
    """
    if programme.kickoff_event_id:
        return programme.kickoff_event_id
    meeting = bind_kickoff(programme.start_at, programme.kickoff_at)
    if meeting is None:
        return None

    company = session.get(Company, programme.company_id)
    company_name = company.name if company else "a company"

    google = get_google_client()
    result = google.create_event(
        EventSpec(
            summary=f"Kickoff — {programme.title} ({company_name})",
            starts_at=meeting,
            ends_at=meeting + timedelta(hours=KICKOFF_DURATION_HOURS),
            description=(
                f"Kickoff call for {programme.title}.\n\n"
                f"Company: {company_name}\n"
                "You'll get the brief, meet the team, and ask questions."
            ),
            with_meet=True,
        )
    )
    programme.kickoff_event_id = result.event_id
    programme.kickoff_meet_link = result.meet_link
    session.flush()
    return result.event_id


def ensure_pitch_event(
    session: Session, programme: Programme, *, starts_at, ends_at
) -> str | None:
    """One Meet for the whole pitching block. Participants join at their slot."""
    if programme.pitch_event_id:
        return programme.pitch_event_id
    if starts_at is None or ends_at is None:
        return None

    company = session.get(Company, programme.company_id)
    company_name = company.name if company else "a company"

    google = get_google_client()
    result = google.create_event(
        EventSpec(
            summary=f"Pitching — {programme.title} ({company_name})",
            starts_at=starts_at,
            ends_at=ends_at,
            description=(
                f"Judging pitches for {programme.title}.\n\n"
                f"Company: {company_name}\n"
                "Join at your booked slot. Stay in this room until you have pitched."
            ),
            with_meet=True,
        )
    )
    programme.pitch_event_id = result.event_id
    programme.pitch_meet_link = result.meet_link
    session.flush()
    return result.event_id
