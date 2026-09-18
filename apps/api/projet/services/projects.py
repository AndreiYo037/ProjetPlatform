"""Project entries — the case-study layer of the profile.

The one rule this module holds: on a verified entry, the facts are the
platform's and the description is the participant's. Seeding copies the
associated experience, the dates and the brief from a programme that actually
ran and leaves the description empty, because nobody but the person who did
the work can write it, and a platform-generated one would make every profile
read the same.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Company,
    Participant,
    Programme,
    ProjectEntry,
    ProjectLink,
    Skill,
)
from projet.models.enums import ArtifactVisibility, ProgrammeStatus
from projet.models.portfolio import ProjectSkill
from projet.storage import get_storage

# What a participant may write on a verified entry: the description and the
# consent to show the work. The title, the associated experience and the
# dates came from a programme this platform ran and stay platform-derived.
VERIFIED_EDITABLE_FIELDS = frozenset({"description", "artifact_visibility", "visible"})
# Everything a self-declared entry has, all of it theirs.
SELF_DECLARED_EDITABLE_FIELDS = VERIFIED_EDITABLE_FIELDS | {
    "title",
    "associated_experience",
    "started_at",
    "ended_at",
    "ongoing",
}

MAX_PROJECT_FILE_BYTES = 20 * 1024 * 1024
ALLOWED_PROJECT_FILE_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ProjectError(Exception):
    """A seed, edit, upload or delete that cannot be honoured."""


def _as_date(value: object) -> date | None:
    return value.date() if value is not None else None  # type: ignore[union-attr]


def seed_from_participant(
    session: Session, person_id: uuid.UUID, participant_id: uuid.UUID
) -> ProjectEntry:
    """Create the verified entry for a completed programme. Idempotent.

    Re-running returns the existing entry untouched rather than resetting it —
    a second click must never wipe a description the participant has since
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
        title=programme.title,
        associated_experience=company.name if company else None,
        started_at=_as_date(programme.start_at),
        ended_at=_as_date(programme.submit_deadline_at),
        # Left empty on purpose. See the module docstring.
        description=None,
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
            ProjectLink(project_entry_id=entry.id, url=programme.brief_url, label="The brief")
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
            # Still running sorts above finished; then most recent first.
            0 if e.ongoing else 1,
            -(e.ended_at.toordinal() if e.ended_at else 0),
        ),
    )


def _owned_entry(session: Session, person_id: uuid.UUID, entry_id: uuid.UUID) -> ProjectEntry:
    entry = session.get(ProjectEntry, entry_id)
    if entry is None or entry.person_id != person_id:
        raise ProjectError("No project there.")
    return entry


def create_entry(
    session: Session,
    person_id: uuid.UUID,
    *,
    title: str,
    associated_experience: str | None = None,
    started_at: date | None = None,
    ended_at: date | None = None,
    ongoing: bool = False,
    description: str | None = None,
    artifact_visibility: ArtifactVisibility = ArtifactVisibility.PRIVATE,
) -> ProjectEntry:
    """A self-declared entry. Verified ones come only from seed_from_participant."""
    if not title.strip():
        raise ProjectError("A title is required.")

    entry = ProjectEntry(
        person_id=person_id,
        participant_id=None,
        title=title.strip(),
        associated_experience=(associated_experience or "").strip() or None,
        started_at=started_at,
        # An end date and "still going" contradict each other; the flag wins,
        # because it is the thing they ticked most recently.
        ended_at=None if ongoing else ended_at,
        ongoing=ongoing,
        description=description,
        artifact_visibility=artifact_visibility,
    )
    session.add(entry)
    session.flush()
    return entry


def update_entry(
    session: Session, person_id: uuid.UUID, entry_id: uuid.UUID, changes: dict
) -> ProjectEntry:
    """Apply `changes` to an entry the caller owns.

    A verified entry only accepts VERIFIED_EDITABLE_FIELDS, refusing anything
    else with a named error rather than quietly dropping it — an attempt to
    rewrite who they worked for should surface, not vanish.
    """
    entry = _owned_entry(session, person_id, entry_id)
    allowed = SELF_DECLARED_EDITABLE_FIELDS if not entry.verified else VERIFIED_EDITABLE_FIELDS
    unknown = set(changes) - allowed
    if unknown:
        raise ProjectError(
            f"Cannot change {', '.join(sorted(unknown))} on a "
            f"{'verified' if entry.verified else 'self-declared'} entry."
        )
    if "title" in changes and not (changes["title"] or "").strip():
        raise ProjectError("A title is required.")

    for field, value in changes.items():
        setattr(entry, field, value)
    if entry.ongoing:
        entry.ended_at = None
    session.flush()
    return entry


def delete_entry(session: Session, person_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    """Self-declared only. A verified entry is a record of a week this platform
    ran, and stays available to hide (`visible=False`) rather than erase."""
    entry = _owned_entry(session, person_id, entry_id)
    if entry.verified:
        raise ProjectError("A verified entry can be hidden, not deleted.")
    for link in entry.links:
        if link.storage_key:
            get_storage().delete(link.storage_key)
    session.delete(entry)
    session.flush()


def add_link(
    session: Session,
    person_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    url: str,
    label: str | None = None,
) -> ProjectLink:
    entry = _owned_entry(session, person_id, entry_id)
    if not url.strip():
        raise ProjectError("A link needs a URL.")
    link = ProjectLink(
        project_entry_id=entry.id, url=url.strip(), label=(label or "").strip() or None
    )
    session.add(link)
    session.flush()
    return link


def attach_file(
    session: Session,
    person_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> ProjectLink:
    """Store an uploaded file against the entry.

    The object is never publicly addressable: it is reached only through an
    expiring signed link, and only when the entry's own consent setting allows
    it (section 8).
    """
    entry = _owned_entry(session, person_id, entry_id)
    if not data:
        raise ProjectError("That file is empty.")
    if len(data) > MAX_PROJECT_FILE_BYTES:
        raise ProjectError("That file is larger than 20MB.")
    if content_type not in ALLOWED_PROJECT_FILE_TYPES:
        raise ProjectError("That file type is not accepted.")

    suffix = ("." + filename.rsplit(".", 1)[1]) if "." in filename else ""
    key = f"projects/{entry.id}/{uuid.uuid4().hex}{suffix}"
    get_storage().put(key, data, content_type)

    link = ProjectLink(
        project_entry_id=entry.id,
        storage_key=key,
        filename=filename,
        content_type=content_type,
        label=filename,
    )
    session.add(link)
    session.flush()
    return link


def remove_link(
    session: Session, person_id: uuid.UUID, entry_id: uuid.UUID, link_id: uuid.UUID
) -> None:
    entry = _owned_entry(session, person_id, entry_id)
    link = session.get(ProjectLink, link_id)
    if link is None or link.project_entry_id != entry.id:
        raise ProjectError("No link there.")
    if link.storage_key:
        get_storage().delete(link.storage_key)
    session.delete(link)
    session.flush()


def set_skills(
    session: Session, person_id: uuid.UUID, entry_id: uuid.UUID, skill_ids: list[uuid.UUID]
) -> ProjectEntry:
    """Replace a self-declared entry's claimed skills.

    Verified entries never take a skill through here: what a verified entry
    demonstrated is for a judge to attest as a ProfileSkill, not for the
    participant to claim, and ProjectSkill exists precisely so a claim can
    never be mistaken for that attestation.
    """
    entry = _owned_entry(session, person_id, entry_id)
    if entry.verified:
        raise ProjectError("Skills on a verified entry come from attestation, not a claim.")

    wanted = set(skill_ids)
    if wanted:
        found = set(session.scalars(select(Skill.id).where(Skill.id.in_(wanted))))
        if wanted - found:
            raise ProjectError("Unknown skill.")

    existing = {
        row.skill_id: row
        for row in session.scalars(
            select(ProjectSkill).where(ProjectSkill.project_entry_id == entry.id)
        )
    }
    for skill_id, row in existing.items():
        if skill_id not in wanted:
            session.delete(row)
    for skill_id in wanted - existing.keys():
        session.add(ProjectSkill(project_entry_id=entry.id, skill_id=skill_id))
    session.flush()
    return entry
