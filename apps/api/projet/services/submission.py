"""Participant submissions (FR-800).

Most slots are Drive links, carried by two requirements:

  * FR-802 — the accessibility check at paste time. This prevents the most
    predictable failure of the whole programme: five dead links on judging day.
  * FR-804 — the deadline snapshot. Locking the link field does not lock the
    document, so the snapshot is what gets judged.

A slot can instead be a direct upload. A static document has no "live" version
to protect against last-minute edits, so an upload skips both: it is stored
once, under the same snapshot fields a Drive link only gets at the deadline,
and there is nothing left for the deadline sweep to do with it.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.integrations.google.client import GoogleClient, get_google_client
from projet.models import Participant, Programme, Submission, SubmissionLink, Team, TeamMember
from projet.models.base import utcnow
from projet.models.enums import (
    AccessStatus,
    ProgrammeStatus,
    SnapshotStatus,
    SubmissionSlot,
    SubmissionStatus,
)
from projet.storage import get_storage


class SubmissionError(RuntimeError):
    pass


@dataclass
class LinkResult:
    """What the participant is told, inline, the moment they paste."""

    slot: str
    access_status: str
    ok: bool
    filename: str | None = None
    mime_type: str | None = None
    message: str | None = None


def submission_for_participant(session: Session, participant: Participant) -> Submission | None:
    return session.scalar(
        select(Submission)
        .join(Team, Submission.team_id == Team.id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.participant_id == participant.id)
    )


def is_locked(session: Session, submission: Submission) -> bool:
    """After the deadline the links are frozen; what exists at 23:59 is what
    gets judged."""
    if submission.status == SubmissionStatus.LOCKED:
        return True
    team = session.get(Team, submission.team_id)
    programme = session.get(Programme, team.programme_id) if team else None
    if programme is None:
        return False
    if programme.submit_deadline_at and utcnow() >= programme.submit_deadline_at:
        return True
    return programme.status in (
        ProgrammeStatus.SUBMITTED,
        ProgrammeStatus.JUDGING,
        ProgrammeStatus.COMPLETE,
    )


def set_link(
    session: Session,
    submission: Submission,
    slot: SubmissionSlot,
    drive_url: str,
    *,
    google: GoogleClient | None = None,
) -> LinkResult:
    """Paste a link, and find out immediately whether we can open it.

    A link we cannot open is recorded as such rather than rejected outright:
    the participant needs to see the failure and fix the sharing setting, and
    the submission simply cannot be complete until they do.
    """
    if is_locked(session, submission):
        raise SubmissionError("The deadline has passed; submissions are locked.")

    link = session.scalar(
        select(SubmissionLink)
        .where(SubmissionLink.submission_id == submission.id)
        .where(SubmissionLink.slot == slot)
    )
    if link is None:
        link = SubmissionLink(submission_id=submission.id, slot=slot)
        session.add(link)

    client = google or get_google_client()
    probe = client.probe_drive_file(drive_url)

    link.drive_url = drive_url.strip()
    link.drive_file_id = probe.file_id
    link.detected_filename = probe.filename
    link.detected_mime = probe.mime_type
    link.access_status = probe.access_status
    link.last_checked_at = utcnow()

    _refresh_status(session, submission)
    session.flush()

    return LinkResult(
        slot=slot.value,
        access_status=probe.access_status.value,
        ok=probe.ok,
        filename=probe.filename,
        mime_type=probe.mime_type,
        message=probe.message,
    )


def set_upload(
    session: Session,
    submission: Submission,
    slot: SubmissionSlot,
    *,
    content: bytes,
    filename: str,
    mime_type: str,
) -> LinkResult:
    """Attach a file directly, skipping the Drive round-trip entirely.

    There is nothing to probe (we just received the bytes) and nothing to
    snapshot later (what we stored is already frozen), so this sets the
    access and snapshot fields in one step rather than waiting on the
    deadline sweep to do the second half.
    """
    if is_locked(session, submission):
        raise SubmissionError("The deadline has passed; submissions are locked.")

    link = session.scalar(
        select(SubmissionLink)
        .where(SubmissionLink.submission_id == submission.id)
        .where(SubmissionLink.slot == slot)
    )
    if link is None:
        link = SubmissionLink(submission_id=submission.id, slot=slot)
        session.add(link)
        session.flush()

    key = f"submissions/{submission.id}/{slot.value}/{secrets.token_hex(8)}.pdf"
    get_storage().put(key, content, mime_type)

    link.drive_url = None
    link.drive_file_id = None
    link.detected_filename = filename
    link.detected_mime = mime_type
    link.access_status = AccessStatus.OK
    link.last_checked_at = utcnow()
    link.snapshot_key = key
    link.snapshot_mime = mime_type
    link.snapshot_bytes = len(content)
    link.snapshot_at = utcnow()
    link.snapshot_status = SnapshotStatus.OK

    _refresh_status(session, submission)
    session.flush()

    return LinkResult(
        slot=slot.value,
        access_status=AccessStatus.OK.value,
        ok=True,
        filename=filename,
        mime_type=mime_type,
    )


def clear_link(session: Session, submission: Submission, slot: SubmissionSlot) -> None:
    if is_locked(session, submission):
        raise SubmissionError("The deadline has passed; submissions are locked.")
    link = session.scalar(
        select(SubmissionLink)
        .where(SubmissionLink.submission_id == submission.id)
        .where(SubmissionLink.slot == slot)
    )
    if link is not None:
        # A Drive link's snapshot only exists after the deadline, and this
        # function already refuses to run past it — so a snapshot present
        # here is always our own upload, never a deadline snapshot, and
        # clearing the slot means deleting the object it points at.
        if link.snapshot_key:
            get_storage().delete(link.snapshot_key)
            link.snapshot_key = None
            link.snapshot_mime = None
            link.snapshot_bytes = None
            link.snapshot_at = None
            link.snapshot_status = SnapshotStatus.PENDING
        link.drive_url = None
        link.drive_file_id = None
        link.detected_filename = None
        link.detected_mime = None
        link.access_status = AccessStatus.UNCHECKED
        link.last_checked_at = None
    _refresh_status(session, submission)
    session.flush()


def _refresh_status(session: Session, submission: Submission) -> None:
    """Complete means every slot has a link we can actually open, or a file
    we already hold — an upload's snapshot_key is set the moment it lands,
    not just at the deadline."""
    links = list(
        session.scalars(select(SubmissionLink).where(SubmissionLink.submission_id == submission.id))
    )
    filled = [link for link in links if link.drive_url or link.snapshot_key]
    complete = (
        bool(links)
        and len(filled) == len(links)
        and all(link.access_status == AccessStatus.OK for link in links)
    )
    if complete:
        submission.status = SubmissionStatus.COMPLETE
        submission.submitted_at = submission.submitted_at or utcnow()
    elif submission.status != SubmissionStatus.LOCKED:
        submission.status = SubmissionStatus.DRAFT
        submission.submitted_at = None


def recheck(
    session: Session, submission: Submission, *, google: GoogleClient | None = None
) -> list[LinkResult]:
    """Re-probe every link. Used by the nightly job and by the participant
    pressing "check again" after fixing a sharing setting."""
    client = google or get_google_client()
    results: list[LinkResult] = []
    for link in session.scalars(
        select(SubmissionLink).where(SubmissionLink.submission_id == submission.id)
    ):
        if not link.drive_url:
            continue
        probe = client.probe_drive_file(link.drive_url)
        link.access_status = probe.access_status
        link.drive_file_id = probe.file_id
        link.detected_filename = probe.filename
        link.detected_mime = probe.mime_type
        link.last_checked_at = utcnow()
        results.append(
            LinkResult(
                slot=link.slot.value,
                access_status=probe.access_status.value,
                ok=probe.ok,
                filename=probe.filename,
                mime_type=probe.mime_type,
                message=probe.message,
            )
        )
    _refresh_status(session, submission)
    session.flush()
    return results
