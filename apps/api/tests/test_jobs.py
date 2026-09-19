"""Scheduled work, and the deadline sweep in particular.

With submission on day 6 and judging on day 7 there are roughly twelve hours
between them and nothing that needs a human can sit in that gap. The sweep is
what makes the pitch schedule exist without admin doing anything.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from projet.jobs.definitions import (
    deadline_sweep,
    due_programmes,
    expire_offers,
    no_submission_report,
    pitch_day_sweep,
    preflight,
    recheck_submission_links,
    response_time_indicator,
)
from projet.models import Application, JudgingSession, Outbox, Thread
from projet.models.enums import (
    AccessStatus,
    ApplicationStatus,
    AuthorRole,
    ParticipantStatus,
    ProgrammeStatus,
    SubmissionStatus,
    ThreadType,
)
from projet.outbox.provisioning import SESSION_REMOVAL
from projet.outbox.snapshots import SNAPSHOT_EFFECT
from projet.services.teams import ensure_submission, ensure_team_for_participant


def _submit(session, participant, *, working: bool = True):
    team = ensure_team_for_participant(session, participant)
    submission = ensure_submission(session, team)
    for link in submission.links:
        link.drive_url = f"https://drive.google.com/file/d/{'x' * 30}/view"
        link.drive_file_id = "x" * 30
        link.detected_mime = "application/pdf"
        link.access_status = AccessStatus.OK if working else AccessStatus.DENIED
    session.flush()
    return submission


def test_offers_expire_and_release_their_seat(session, programme, participant_factory):
    participant = participant_factory()
    application = session.get(Application, participant.application_id)
    application.status = ApplicationStatus.OFFERED
    application.offer_expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.flush()

    assert expire_offers(session) == 1
    assert application.status == ApplicationStatus.EXPIRED


def test_a_live_offer_is_left_alone(session, programme, participant_factory):
    participant = participant_factory()
    application = session.get(Application, participant.application_id)
    application.status = ApplicationStatus.OFFERED
    application.offer_expires_at = datetime.now(UTC) + timedelta(hours=10)
    session.flush()

    assert expire_offers(session) == 0
    assert application.status == ApplicationStatus.OFFERED


def test_deadline_sweep_locks_submissions_and_queues_snapshots(
    session, programme, judging_session, participant_factory
):
    participant = participant_factory()
    participant.judging_session_id = judging_session.id
    submission = _submit(session, participant)
    programme.submit_deadline_at = datetime.now(UTC) - timedelta(minutes=1)
    session.flush()

    result = deadline_sweep(session)

    assert result.programmes_processed == 1
    assert submission.status == SubmissionStatus.LOCKED
    assert submission.locked_at is not None
    assert participant.status == ParticipantStatus.SUBMITTED
    assert result.snapshots_queued == 2
    queued = {row.effect_type for row in session.scalars(select(Outbox))}
    assert SNAPSHOT_EFFECT in queued


def test_an_uploaded_slot_is_locked_but_not_requeued_for_snapshotting(
    session, programme, judging_session, participant_factory
):
    """An upload's frozen copy is set the moment it lands, not at the
    deadline, so the sweep has nothing left to do for that slot — only the
    Drive-linked one alongside it needs fetching."""
    from projet.models.enums import SubmissionSlot
    from projet.services.submission import set_upload

    participant = participant_factory()
    participant.judging_session_id = judging_session.id
    submission = _submit(session, participant)
    set_upload(
        session, submission, SubmissionSlot.MEMO, content=b"%PDF-1.4", filename="memo.pdf",
        mime_type="application/pdf",
    )
    programme.submit_deadline_at = datetime.now(UTC) - timedelta(minutes=1)
    session.flush()

    result = deadline_sweep(session)

    assert submission.status == SubmissionStatus.LOCKED
    assert result.snapshots_queued == 1
    queued = list(session.scalars(select(Outbox).where(Outbox.effect_type == SNAPSHOT_EFFECT)))
    assert len(queued) == 1
    assert queued[0].subject_id == next(
        link.id for link in submission.links if link.slot == SubmissionSlot.ARTIFACT
    )


def test_non_submitters_are_flagged_and_taken_off_their_session(
    session, programme, judging_session, participant_factory
):
    """FR-811c — the deadline passes, non-submitters drop off their slot, and
    the schedule is already correct."""
    submitted = participant_factory()
    submitted.judging_session_id = judging_session.id
    _submit(session, submitted)

    absent = participant_factory()
    absent.judging_session_id = judging_session.id

    broken = participant_factory()
    broken.judging_session_id = judging_session.id
    _submit(session, broken, working=False)

    programme.submit_deadline_at = datetime.now(UTC) - timedelta(minutes=1)
    session.flush()
    result = deadline_sweep(session)

    assert result.non_submitters == 2
    assert absent.status == ParticipantStatus.NO_SUBMISSION
    assert broken.status == ParticipantStatus.NO_SUBMISSION, (
        "a link we cannot open is not a submission"
    )
    removals = [r for r in session.scalars(select(Outbox)) if r.effect_type == SESSION_REMOVAL]
    assert len(removals) == 2
    assert no_submission_report(session, programme.id)


def test_the_sweep_claims_each_programme_exactly_once(session, programme, participant_factory):
    """A restart mid-sweep must not re-run anything, which is why the claim is a
    column and not an in-memory flag."""
    participant_factory()
    programme.submit_deadline_at = datetime.now(UTC) - timedelta(minutes=1)
    session.flush()

    first = deadline_sweep(session)
    second = deadline_sweep(session)

    assert first.programmes_processed == 1
    assert second.programmes_processed == 0
    assert programme.deadline_processed_at is not None
    assert programme.status == ProgrammeStatus.SUBMITTED


def test_a_programme_before_its_deadline_is_not_due(session, programme):
    programme.submit_deadline_at = datetime.now(UTC) + timedelta(days=1)
    session.flush()
    assert due_programmes(session) == []


def test_nightly_recheck_catches_a_link_unshared_after_submission(
    session, programme, participant_factory, google
):
    """A link shareable on day 2 can be un-shared by day 5, and nobody finds out
    unless we look."""
    participant = participant_factory()
    submission = _submit(session, participant)
    url = submission.links[0].drive_url
    google.stage_denied(url)

    broken = recheck_submission_links(session, google)

    assert len(broken) >= 1
    assert broken[0].access_status == AccessStatus.DENIED


def test_response_time_indicator_surfaces_a_quiet_rep(session, programme):
    """FR-614b — visibility without obligation."""
    session.add(
        Thread(
            programme_id=programme.id,
            type=ThreadType.QUESTION_CHALLENGE,
            title="Is revenue net or gross?",
            author_role=AuthorRole.PARTICIPANT,
            created_at=datetime.now(UTC) - timedelta(hours=30),
        )
    )
    session.flush()

    indicator = response_time_indicator(session, programme.id)

    assert indicator["outstanding"] == 1
    assert indicator["oldest_age_hours"] >= 29


def test_preflight_lists_only_the_participants_with_a_problem(
    session, programme, judging_session, participant_factory
):
    """FR-1501 — a checklist of failures, not a green tick."""
    ready = participant_factory()
    ready.judging_session_id = judging_session.id
    ready.gmail_thread_id = "thread-1"

    not_ready = participant_factory()
    not_ready.person.google_email = None
    session.flush()

    failures = preflight(session, programme.id)
    ids = {row["participant_id"] for row in failures}

    assert not_ready.id in ids
    assert ready.id not in ids


def _booked_pitch(session, programme, participant_factory, *, excluded=False):
    from projet.services.schedule import PROGRAMME_TZ

    starts = datetime(2026, 9, 23, 14, 0, tzinfo=PROGRAMME_TZ)
    programme.pitch_starts_at = starts
    programme.pitch_duration_minutes = 15
    programme.pitch_meet_link = "https://meet.google.com/pitch-room"
    person = participant_factory()
    person.excluded = excluded
    slot = JudgingSession(
        programme_id=programme.id,
        starts_at=starts,
        ends_at=starts + timedelta(minutes=15),
        capacity=1,
        location_or_meet_link=programme.pitch_meet_link,
    )
    session.add(slot)
    session.flush()
    person.judging_session_id = slot.id
    session.flush()
    return person


def test_pitch_day_email_waits_until_midnight_sgt(
    session, programme, participant_factory
):
    from projet.services.schedule import PROGRAMME_TZ

    _booked_pitch(session, programme, participant_factory)
    waiting = datetime(2026, 9, 22, 23, 59, tzinfo=PROGRAMME_TZ)

    result = pitch_day_sweep(session, now=waiting)

    assert result.programmes_processed == 0
    assert result.emails_queued == 0
    assert programme.pitch_day_emailed_at is None


def test_pitch_day_email_sends_slot_and_meet_at_midnight(
    session, programme, participant_factory, google
):
    from projet.outbox.provisioning import PITCH_DAY_EMAIL
    from projet.outbox.worker import run_once
    from projet.services.schedule import PROGRAMME_TZ

    booked = _booked_pitch(session, programme, participant_factory)
    unbooked = participant_factory()
    midnight = datetime(2026, 9, 23, 0, 0, tzinfo=PROGRAMME_TZ)

    result = pitch_day_sweep(session, now=midnight)
    run_once(session, google)

    assert result.programmes_processed == 1
    assert result.emails_queued == 1
    assert programme.pitch_day_emailed_at == midnight
    queued = [row for row in session.scalars(select(Outbox)) if row.effect_type == PITCH_DAY_EMAIL]
    assert len(queued) == 1
    assert queued[0].subject_id == booked.id
    send = google.calls_of("send_email")[0]
    assert send.payload["to"] == booked.person.contact_email
    assert send.payload["subject"].startswith("Judging today")
    assert "Wednesday 23 September, 14:00" in send.payload["html_body"]
    assert "https://meet.google.com/pitch-room" in send.payload["html_body"]
    assert unbooked.person.contact_email not in [
        call.payload["to"] for call in google.calls_of("send_email")
    ]


def test_a_late_sweep_still_sends_once(session, programme, participant_factory, google):
    """If the clock is already past 00:00, the next sweep catches up — once."""
    from projet.outbox.worker import run_once
    from projet.services.schedule import PROGRAMME_TZ

    _booked_pitch(session, programme, participant_factory)
    afternoon = datetime(2026, 9, 23, 15, 0, tzinfo=PROGRAMME_TZ)

    first = pitch_day_sweep(session, now=afternoon)
    second = pitch_day_sweep(session, now=afternoon)
    run_once(session, google)

    assert first.programmes_processed == 1
    assert first.emails_queued == 1
    assert second.programmes_processed == 0
    assert len(google.calls_of("send_email")) == 1


def test_an_excluded_candidate_is_not_mailed_on_pitch_day(
    session, programme, participant_factory, google
):
    from projet.outbox.worker import run_once
    from projet.services.schedule import PROGRAMME_TZ

    _booked_pitch(session, programme, participant_factory, excluded=True)
    midnight = datetime(2026, 9, 23, 0, 0, tzinfo=PROGRAMME_TZ)

    result = pitch_day_sweep(session, now=midnight)
    run_once(session, google)

    assert result.emails_queued == 0
    assert google.calls_of("send_email") == []
