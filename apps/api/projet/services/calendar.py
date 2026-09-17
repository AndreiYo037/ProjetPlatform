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

    google = get_google_client()
    result = google.create_event(
        EventSpec(
            summary=f"Kickoff — {programme.title} ({company_name})",
            starts_at=programme.start_at,
            ends_at=programme.start_at + timedelta(hours=1),
            description=(
                f"Kickoff call for {programme.title}.\n\n"
                f"Company: {company_name}\n"
                f"You'll get the brief, meet the team, and ask questions."
            ),
            with_meet=True,
        )
    )
    programme.kickoff_event_id = result.event_id
    programme.kickoff_meet_link = result.meet_link
    session.flush()
    return result.event_id
