"""Calendar event creation for programme milestones.

The kickoff event is created when a programme is published (start_at is
confirmed at that point) and stored on the programme. Accepted participants
are added as attendees via the provisioning chain's KICKOFF_INVITE effect.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from projet.integrations.google.client import EventSpec, get_google_client
from projet.models import Company, Programme
from projet.services.schedule import kickoff_meeting_at


def ensure_kickoff_event(session: Session, programme: Programme) -> str | None:
    """Create the kickoff Calendar event if it doesn't exist yet.

    Returns the event_id, or None if the programme has no start_at.
    """
    if programme.kickoff_event_id:
        return programme.kickoff_event_id
    if programme.start_at is None:
        return None

    company = session.get(Company, programme.company_id)
    company_name = company.name if company else "a company"

    meeting = kickoff_meeting_at(programme.start_at)
    google = get_google_client()
    result = google.create_event(
        EventSpec(
            summary=f"Kickoff — {programme.title} ({company_name})",
            starts_at=meeting,
            ends_at=meeting + timedelta(hours=1),
            description=(
                f"Kickoff call for {programme.title}.\n\n"
                f"Company: {company_name}\n"
                "You'll get the brief, meet the team, and ask questions.\n\n"
                # The invite reaches people who have been offered a place but
                # not yet taken it, and Yes here is an RSVP to Google, nothing
                # more. Said on the invite itself because this is the screen
                # where the mistake gets made.
                "If you have been offered a place and not yet accepted it, "
                "replying Yes here does not confirm it. Use the Accept link in "
                "your offer email."
            ),
            with_meet=True,
        )
    )
    programme.kickoff_event_id = result.event_id
    programme.kickoff_meet_link = result.meet_link
    session.flush()
    return result.event_id
