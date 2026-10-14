"""Participant submissions (FR-800).

Link slots accept any URL. Google Drive links still get the accessibility
check at paste time (FR-802), because a Drive file with the wrong sharing
setting is the failure judging day cannot recover from. Everything else
(GitHub, Figma, a personal site, a Notion page) is stored as given: we
cannot open those the way we open Drive, and refusing them is worse than
taking the participant at their word.

A slot can instead be a direct upload. A static document has no "live" version
to protect against last-minute edits, so an upload skips both: it is stored
once, under the same snapshot fields a Drive link only gets at the deadline,
and there is nothing left for the deadline sweep to do with it.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.integrations.google.client import GoogleClient, get_google_client
from projet.integrations.google.urls import extract_file_id
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


_HAS_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def normalise_pasted_url(url: str) -> str:
    """Make a pasted address open off-site, not as a path on this app.

    `www.tiktok.com` has no scheme, so an href treats it as relative and a
    judge lands on /judging/www.tiktok.com. Prefix https when none is given.
    """
    url = url.strip()
    if not url:
        return url
    if _HAS_SCHEME.match(url):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"https://{url}"


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


def _programme_for(session: Session, submission: Submission) -> Programme | None:
    team = session.get(Team, submission.team_id)
    return session.get(Programme, team.programme_id) if team else None


def assert_submissions_open(session: Session, submission: Submission) -> None:
    """Refuse edits until start_at, when the company opens the work window."""
    from projet.services.schedule import submissions_open

    programme = _programme_for(session, submission)
    if programme is not None and not submissions_open(programme):
        raise SubmissionError("Submissions open when the challenge starts. Come back then.")


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
    assert_submissions_open(session, submission)

    url = normalise_pasted_url(drive_url)
    if not url:
        raise SubmissionError("Paste a link.")

    link = session.scalar(
        select(SubmissionLink)
        .where(SubmissionLink.submission_id == submission.id)
        .where(SubmissionLink.slot == slot)
    )
    if link is None:
        link = SubmissionLink(submission_id=submission.id, slot=slot)
        session.add(link)

    if extract_file_id(url):
        client = google or get_google_client()
        probe = client.probe_drive_file(url)
        link.drive_url = url
        link.drive_file_id = probe.file_id
        link.detected_filename = probe.filename
        link.detected_mime = probe.mime_type
        link.access_status = probe.access_status
        link.last_checked_at = utcnow()
        result = LinkResult(
            slot=slot.value,
            access_status=probe.access_status.value,
            ok=probe.ok,
            filename=probe.filename,
            mime_type=probe.mime_type,
            message=probe.message,
        )
    else:
        link.drive_url = url
        link.drive_file_id = None
        link.detected_filename = None
        link.detected_mime = None
        link.access_status = AccessStatus.OK
        link.last_checked_at = utcnow()
        result = LinkResult(
            slot=slot.value,
            access_status=AccessStatus.OK.value,
            ok=True,
        )

    _refresh_status(session, submission)
    session.flush()
    return result


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
    assert_submissions_open(session, submission)

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
    assert_submissions_open(session, submission)
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


MEMO_MAX_CHARS = 10_000


def memo_missing(submission: Submission) -> bool:
    """True when the memo still has to be written. NULL on an already
    handed-in submission is the grandfathered case: it predates the memo."""
    if submission.memo_text is None:
        return submission.submitted_at is None
    return not submission.memo_text.strip()


PITCH_MODES = ("online", "onsite")


def pitch_mode_required(session: Session, submission: Submission) -> bool:
    """On-site challenges ask how the team will pitch; online ones do not.
    A hand-in from before the question existed is not asked retroactively."""
    programme = _programme_for(session, submission)
    if programme is None or not programme.onsite:
        return False
    return not (submission.pitch_mode is None and submission.submitted_at is not None)


def pitch_mode_missing(session: Session, submission: Submission) -> bool:
    return pitch_mode_required(session, submission) and submission.pitch_mode is None


def set_pitch_mode(session: Session, submission: Submission, mode: str) -> None:
    if is_locked(session, submission):
        raise SubmissionError("Submissions are locked.")
    assert_submissions_open(session, submission)
    programme = _programme_for(session, submission)
    if programme is None or not programme.onsite:
        raise SubmissionError("Only on-site challenges ask how you will pitch.")
    if mode not in PITCH_MODES:
        raise SubmissionError("Choose online or on-site.")
    submission.pitch_mode = mode
    session.flush()
    _refresh_status(session, submission)


def set_memo(session: Session, submission: Submission, text: str) -> None:
    if is_locked(session, submission):
        raise SubmissionError("Submissions are locked.")
    assert_submissions_open(session, submission)
    text = text.strip()
    if len(text) > MEMO_MAX_CHARS:
        raise SubmissionError(f"Keep the memo under {MEMO_MAX_CHARS:,} characters.")
    submission.memo_text = text
    session.flush()
    _refresh_status(session, submission)


def _refresh_status(session: Session, submission: Submission) -> None:
    """Complete means the required slots are filled and openable. That is not a
    hand-in; submit_work stamps submitted_at, and that is what opens a timeslot.

    The artifact link and the typed memo are both required. A submission that
    was handed in before the memo existed (memo_text still NULL) stays valid.
    """
    links = list(
        session.scalars(select(SubmissionLink).where(SubmissionLink.submission_id == submission.id))
    )
    required = [link for link in links if link.slot == SubmissionSlot.ARTIFACT]
    if not required:
        required = [link for link in links if link.slot != SubmissionSlot.MEMO]
    filled = [link for link in required if link.drive_url or link.snapshot_key]
    complete = (
        bool(required)
        and len(filled) == len(required)
        and all(link.access_status == AccessStatus.OK for link in required)
        and not memo_missing(submission)
        and not pitch_mode_missing(session, submission)
    )
    if complete:
        submission.status = SubmissionStatus.COMPLETE
    elif submission.status != SubmissionStatus.LOCKED:
        submission.status = SubmissionStatus.DRAFT
        submission.submitted_at = None
    _resize_pitch_grid(session, submission)


def _resize_pitch_grid(session: Session, submission: Submission) -> None:
    team = session.get(Team, submission.team_id)
    if team is None:
        return
    programme = session.get(Programme, team.programme_id)
    if programme is None:
        return
    from projet.services.pitch import ensure_free_pitch_slot

    ensure_free_pitch_slot(session, programme)


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
        if not extract_file_id(link.drive_url):
            link.access_status = AccessStatus.OK
            link.last_checked_at = utcnow()
            results.append(
                LinkResult(
                    slot=link.slot.value,
                    access_status=AccessStatus.OK.value,
                    ok=True,
                )
            )
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


def submit_work(
    session: Session, submission: Submission, *, google: GoogleClient | None = None
) -> Submission:
    """The hand-in. Filling slots is not enough — this is what opens a timeslot."""
    if is_locked(session, submission):
        raise SubmissionError("The deadline has passed; submissions are locked.")
    assert_submissions_open(session, submission)
    recheck(session, submission, google=google)
    if submission.status != SubmissionStatus.COMPLETE:
        if pitch_mode_missing(session, submission):
            raise SubmissionError(
                "Choose whether you will pitch online or on-site before you submit."
            )
        raise SubmissionError("Add your work link and write your memo before you submit.")
    submission.submitted_at = utcnow()
    _resize_pitch_grid(session, submission)
    session.flush()
    return submission
