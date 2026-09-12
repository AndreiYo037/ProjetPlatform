"""The provisioning chain (FR-1400).

Sessions are assigned at acceptance, not after the deadline: with roughly twelve
hours between submission and judging, nothing requiring a human can sit in that
gap (FR-811b).
"""

from __future__ import annotations

from sqlalchemy import func, select

from projet.models import JudgingSession, Outbox, Participant
from projet.models.base import utcnow
from projet.models.enums import OutboxStatus
from projet.outbox.provisioning import (
    JUDGING_SESSION_INVITE,
    assign_judging_session,
    enqueue_provisioning_chain,
    randomise_run_order,
)
from projet.outbox.worker import run_once


def test_acceptance_assigns_a_session_and_a_run_order(
    session, programme, judging_session, participant_factory
):
    participant = participant_factory()
    chosen = assign_judging_session(session, participant)

    assert chosen is not None
    assert participant.judging_session_id == judging_session.id
    assert participant.run_order == 1


def test_sessions_fill_evenly_rather_than_all_landing_in_the_first(
    session, programme, judging_session, participant_factory
):
    """Session length is the real constraint with no participant cap: twelve
    pitches is a comfortable evening, thirty is four hours."""
    from datetime import timedelta

    second = JudgingSession(
        programme_id=programme.id,
        starts_at=judging_session.starts_at + timedelta(days=1),
        google_event_id="evt-judging-2",
        capacity=12,
    )
    session.add(second)
    session.flush()

    for _ in range(6):
        assign_judging_session(session, participant_factory())
    session.flush()

    counts = dict(
        session.execute(
            select(JudgingSession.id, func.count())
            .join(Participant, Participant.judging_session_id == JudgingSession.id)
            .group_by(JudgingSession.id)
        ).all()
    )
    assert sorted(counts.values()) == [3, 3]


def test_a_full_session_is_skipped(session, programme, judging_session, participant_factory):
    judging_session.capacity = 1
    session.flush()
    first = participant_factory()
    assign_judging_session(session, first)
    session.flush()

    second = participant_factory()
    assign_judging_session(session, second)
    # Only one session exists, so it falls back rather than leaving them unassigned:
    # an unassigned participant on judging night is worse than an over-full session.
    assert second.judging_session_id == judging_session.id


def test_run_order_is_generated_not_curated(
    session, programme, judging_session, participant_factory
):
    """FR-811d — acceptance order correlates with how fast someone checked their
    email, which is not a reason to pitch first."""
    for _ in range(5):
        assign_judging_session(session, participant_factory())
    session.flush()

    ordered = randomise_run_order(session, judging_session.id)
    positions = sorted(p.run_order for p in ordered)

    assert positions == [1, 2, 3, 4, 5]


def test_the_chain_runs_and_each_step_is_separately_retryable(
    session, programme, judging_session, participant_factory, google
):
    participant = participant_factory()
    assign_judging_session(session, participant)
    rows = enqueue_provisioning_chain(
        session,
        participant,
        kickoff_event_id="evt-kickoff",
        deadline_event_id="evt-deadline",
    )
    session.flush()

    assert len(rows) == 4
    run_once(session, google)

    statuses = {row.effect_type: row.status for row in session.scalars(select(Outbox))}
    assert all(status == OutboxStatus.DONE for status in statuses.values())
    assert participant.gmail_thread_id, "the welcome email opens the person's thread"
    assert len(google.calls_of("patch_event_attendees")) == 3
    assert len(google.calls_of("send_email")) == 1


def test_a_calendar_timeout_does_not_resend_the_welcome_email(
    session, programme, judging_session, participant_factory, google
):
    """The exact failure the outbox exists to prevent."""
    from projet.integrations.google.client import TransientGoogleError

    participant = participant_factory()
    assign_judging_session(session, participant)
    enqueue_provisioning_chain(session, participant, kickoff_event_id="evt-kickoff")
    session.flush()

    google.fail_next = TransientGoogleError("calendar timed out")
    run_once(session, google)
    first_sends = len(google.calls_of("send_email"))

    # The sweep comes round again.
    for row in session.scalars(select(Outbox)):
        row.next_attempt_at = utcnow()
    session.flush()
    run_once(session, google)

    assert len(google.calls_of("send_email")) == first_sends == 1


def test_the_calendar_invite_goes_to_the_google_account(
    session, programme, judging_session, participant_factory, google
):
    """FR-204 — the invite has to land on an account that can open Meet."""
    participant = participant_factory()
    participant.person.google_email = "sam.google@gmail.com"
    participant.person.contact_email = "sam@school.test"
    assign_judging_session(session, participant)
    enqueue_provisioning_chain(session, participant)
    session.flush()
    run_once(session, google)

    patch = google.calls_of("patch_event_attendees")[0]
    assert patch.payload["add"][0].email == "sam.google@gmail.com"


def test_welcome_email_goes_to_the_contact_address(
    session, programme, judging_session, participant_factory, google
):
    participant = participant_factory()
    participant.person.contact_email = "sam@school.test"
    enqueue_provisioning_chain(session, participant)
    session.flush()
    run_once(session, google)

    send = google.calls_of("send_email")[0]
    assert send.payload["to"] == "sam@school.test"


def test_a_missing_judging_session_fails_permanently_rather_than_retrying(
    session, programme, participant_factory, google
):
    from projet.models.enums import OutboxSubjectType
    from projet.outbox.effects import enqueue

    participant = participant_factory()
    row = enqueue(
        session,
        subject_type=OutboxSubjectType.PARTICIPANT,
        subject_id=participant.id,
        effect_type=JUDGING_SESSION_INVITE,
    )
    session.flush()
    run_once(session, google)

    assert row.status == OutboxStatus.FAILED
    assert row.attempts == 1
