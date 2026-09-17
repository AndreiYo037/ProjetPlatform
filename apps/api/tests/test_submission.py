"""Drive-link submission (FR-800).

The failure this whole area exists to prevent: five dead links on judging day.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from projet.models.base import utcnow
from projet.models.enums import ProgrammeStatus, SnapshotStatus, SubmissionSlot, SubmissionStatus
from projet.services.submission import (
    SubmissionError,
    clear_link,
    is_locked,
    recheck,
    set_link,
    set_upload,
)
from projet.services.teams import ensure_submission, ensure_team_for_participant

GOOD_URL = "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz01234567/edit"
OTHER_URL = "https://docs.google.com/spreadsheets/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765432/edit"


@pytest.fixture
def submission(session, participant_factory):
    participant = participant_factory()
    team = ensure_team_for_participant(session, participant)
    return participant, ensure_submission(session, team)


def test_pasting_a_good_link_confirms_the_file(session, submission, google):
    _, sub = submission
    result = set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)

    assert result.ok
    assert result.access_status == "ok"
    assert result.filename


def test_a_link_we_cannot_open_says_exactly_what_to_fix(session, submission, google):
    """The message has to be actionable: the participant is the only one who
    can change the sharing setting."""
    _, sub = submission
    google.stage_denied(GOOD_URL)
    result = set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)

    assert not result.ok
    assert result.access_status == "denied"
    assert "Anyone with the link can view" in (result.message or "")


def test_a_submission_is_not_complete_while_any_link_fails(session, submission, google):
    """FR-802 — this is what stops a broken link reaching judging day."""
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    google.stage_denied(OTHER_URL)
    set_link(session, sub, SubmissionSlot.MEMO, OTHER_URL, google=google)

    assert sub.status == SubmissionStatus.DRAFT
    assert sub.submitted_at is None


def test_a_submission_completes_when_every_slot_opens(session, submission, google):
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_link(session, sub, SubmissionSlot.MEMO, OTHER_URL, google=google)

    assert sub.status == SubmissionStatus.COMPLETE
    assert sub.submitted_at is not None


def test_links_can_be_changed_freely_before_the_deadline(session, submission, google):
    """FR-803."""
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_link(session, sub, SubmissionSlot.ARTIFACT, OTHER_URL, google=google)

    link = next(link for link in sub.links if link.slot == SubmissionSlot.ARTIFACT)
    assert link.drive_url == OTHER_URL


def test_clearing_a_link_drops_the_submission_out_of_complete(session, submission, google):
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_link(session, sub, SubmissionSlot.MEMO, OTHER_URL, google=google)
    assert sub.status == SubmissionStatus.COMPLETE

    clear_link(session, sub, SubmissionSlot.ARTIFACT)
    assert sub.status == SubmissionStatus.DRAFT


def test_the_deadline_locks_submissions(session, programme, submission, google):
    _, sub = submission
    programme.submit_deadline_at = utcnow() - timedelta(minutes=1)
    session.flush()

    assert is_locked(session, sub)
    with pytest.raises(SubmissionError, match="locked"):
        set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)


def test_a_judging_programme_is_locked_regardless_of_clock(session, programme, submission, google):
    _, sub = submission
    programme.submit_deadline_at = utcnow() + timedelta(days=2)
    programme.status = ProgrammeStatus.JUDGING
    session.flush()

    assert is_locked(session, sub)


def test_recheck_catches_a_link_unshared_after_pasting(session, submission, google):
    """A link shareable on day 2 can be un-shared by day 5."""
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_link(session, sub, SubmissionSlot.MEMO, OTHER_URL, google=google)
    assert sub.status == SubmissionStatus.COMPLETE

    google.stage_denied(GOOD_URL)
    results = recheck(session, sub, google=google)

    assert any(not r.ok for r in results)
    assert sub.status == SubmissionStatus.DRAFT


def test_a_recheck_after_fixing_sharing_restores_complete(session, submission, google):
    _, sub = submission
    google.stage_denied(GOOD_URL)
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_link(session, sub, SubmissionSlot.MEMO, OTHER_URL, google=google)
    assert sub.status == SubmissionStatus.DRAFT

    google.drive_files.pop(GOOD_URL)  # they fixed the sharing setting
    recheck(session, sub, google=google)
    assert sub.status == SubmissionStatus.COMPLETE


def test_any_url_is_accepted(session, submission, google):
    """Artifact and extra slots take any link, not only Drive."""
    _, sub = submission
    result = set_link(
        session, sub, SubmissionSlot.ARTIFACT, "https://github.com/org/repo", google=google
    )

    assert result.ok
    assert result.access_status == "ok"
    link = next(link for link in sub.links if link.slot == SubmissionSlot.ARTIFACT)
    assert link.drive_url == "https://github.com/org/repo"
    assert link.drive_file_id is None


def test_a_url_without_a_scheme_is_stored_as_https(session, submission, google):
    """Otherwise a judge's Link click is a relative path on the scoring card."""
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, "www.tiktok.com/@someone", google=google)
    link = next(link for link in sub.links if link.slot == SubmissionSlot.ARTIFACT)
    assert link.drive_url == "https://www.tiktok.com/@someone"


def test_an_uploaded_file_is_stored_and_marked_ok(session, submission):
    """A memo is one static document, so upload skips the Drive round-trip
    entirely and is complete the moment the bytes land."""
    _, sub = submission
    result = set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"%PDF-1.4 memo",
        filename="memo.pdf",
        mime_type="application/pdf",
    )

    link = next(link for link in sub.links if link.slot == SubmissionSlot.MEMO)
    assert result.ok
    assert link.access_status.value == "ok"
    assert link.drive_url is None
    assert link.snapshot_status == SnapshotStatus.OK
    assert link.snapshot_key
    from projet.storage import get_storage

    assert get_storage().get(link.snapshot_key) == b"%PDF-1.4 memo"


def test_an_upload_completes_the_submission_alongside_a_link(session, submission, google):
    _, sub = submission
    set_link(session, sub, SubmissionSlot.ARTIFACT, GOOD_URL, google=google)
    set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"%PDF-1.4",
        filename="memo.pdf",
        mime_type="application/pdf",
    )

    assert sub.status == SubmissionStatus.COMPLETE
    assert sub.submitted_at is not None


def test_clearing_an_upload_deletes_the_stored_file(session, submission):
    _, sub = submission
    set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"%PDF-1.4",
        filename="memo.pdf",
        mime_type="application/pdf",
    )
    link = next(link for link in sub.links if link.slot == SubmissionSlot.MEMO)
    key = link.snapshot_key

    from projet.storage import StorageError, get_storage

    clear_link(session, sub, SubmissionSlot.MEMO)
    assert link.snapshot_key is None
    assert link.access_status.value == "unchecked"
    with pytest.raises(StorageError):
        get_storage().get(key)


def test_an_upload_can_be_replaced(session, submission):
    _, sub = submission
    set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"first",
        filename="a.pdf",
        mime_type="application/pdf",
    )
    set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"second",
        filename="b.pdf",
        mime_type="application/pdf",
    )

    link = next(link for link in sub.links if link.slot == SubmissionSlot.MEMO)
    from projet.storage import get_storage

    assert get_storage().get(link.snapshot_key) == b"second"
    assert link.detected_filename == "b.pdf"


def test_the_deadline_locks_an_uploaded_slot_too(session, programme, submission):
    _, sub = submission
    set_upload(
        session,
        sub,
        SubmissionSlot.MEMO,
        content=b"%PDF-1.4",
        filename="memo.pdf",
        mime_type="application/pdf",
    )
    programme.submit_deadline_at = utcnow() - timedelta(minutes=1)
    session.flush()

    assert is_locked(session, sub)
    with pytest.raises(SubmissionError, match="locked"):
        set_upload(
            session,
            sub,
            SubmissionSlot.MEMO,
            content=b"new",
            filename="c.pdf",
            mime_type="application/pdf",
        )
