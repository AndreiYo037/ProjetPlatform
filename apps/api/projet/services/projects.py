"""Project entries — the case-study layer of the profile.

The one rule this module exists to hold: on a verified entry, the facts are
the platform's and the narrative is the participant's. Seeding copies the
organisation, the dates and the brief from a programme that actually ran and
leaves problem / approach / contribution / outcome empty, because nobody but
the person who did the work can write those, and a platform-generated
narrative would be the fastest way to make every profile read the same.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Company,
    Participant,
    Programme,
    ProjectEntry,
    ProjectLink,
)
from projet.models.enums import (
    ArtifactVisibility,
    ProgrammeStatus,
    ProjectKind,
    ProjectLinkKind,
)


class ProjectError(Exception):
    """A seed that cannot be honoured."""


def _as_date(value):  # type: ignore[no-untyped-def]
    return value.date() if value is not None else None


def seed_from_participant(
    session: Session, person_id: uuid.UUID, participant_id: uuid.UUID
) -> ProjectEntry:
    """Create the verified entry for a completed programme. Idempotent.

    Re-running returns the existing entry untouched rather than resetting it —
    a second click must never wipe a narrative the participant has since
    written.
    """
    participant = session.get(Participant, participant_id)
    if participant is None or participant.person_id != person_id:
        raise ProjectError("That programme is not yours.")

    programme = session.get(Programme, participant.programme_id)
    if programme is None:
        raise ProjectError("That programme no longer exists.")
    # Before the close-out there is nothing to show: no pitch happened, no
    # judge tagged anything, and an entry created now would claim a week that
    # has not been finished.
    if programme.status is not ProgrammeStatus.COMPLETE:
        raise ProjectError("This programme has not finished yet.")

    existing = session.scalars(
        select(ProjectEntry).where(ProjectEntry.participant_id == participant_id)
    ).first()
    if existing is not None:
        return existing

    company = session.get(Company, programme.company_id)

    entry = ProjectEntry(
        person_id=person_id,
        participant_id=participant_id,
        kind=ProjectKind.PROGRAMME,
        title=programme.title,
        organisation_name=company.name if company else None,
        started_at=_as_date(programme.start_at),
        ended_at=_as_date(programme.submit_deadline_at),
        # Left empty on purpose. See the module docstring.
        problem=None,
        approach=None,
        contribution=[],
        outcome=None,
        artifact_visibility=ArtifactVisibility.PRIVATE,
        sort_order=0,
    )
    session.add(entry)
    session.flush()

    # The brief is the company's own published description of the work, so it
    # carries over. The submission does not: it can contain the company's data
    # pack, and that needs its own act of consent.
    if programme.brief_url:
        session.add(
            ProjectLink(
                project_entry_id=entry.id,
                kind=ProjectLinkKind.BRIEF,
                url=programme.brief_url,
                label="The brief",
            )
        )
    session.flush()
    return entry


def entries_for(
    session: Session, person_id: uuid.UUID, *, include_hidden: bool = False
) -> list[ProjectEntry]:
    """A person's entries, verified first.

    Verified first is the whole ordering rule: self-declared work counts and is
    shown, but it never outranks a week a company watched, however recent or
    however well written.
    """
    query = select(ProjectEntry).where(ProjectEntry.person_id == person_id)
    if not include_hidden:
        query = query.where(ProjectEntry.visible.is_(True))
    rows = list(session.scalars(query))
    return sorted(
        rows,
        key=lambda e: (
            0 if e.participant_id is not None else 1,
            e.sort_order,
            # Most recent first within a band; entries with no end date last.
            -(e.ended_at.toordinal() if e.ended_at else 0),
        ),
    )
