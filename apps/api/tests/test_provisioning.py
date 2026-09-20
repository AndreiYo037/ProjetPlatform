"""The provisioning chain (FR-1400).

Sessions are assigned at acceptance, not after the deadline: with roughly twelve
hours between submission and judging, nothing requiring a human can sit in that
gap (FR-811b).
"""

from __future__ import annotations

from sqlalchemy import func, select

from projet.models import JudgingSession, Outbox, Participant
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


def test_the_chain_queues_nothing_now_calendar_invites_are_gone(
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

    assert rows == []
    run_once(session, google)
    assert google.calls_of("patch_event_attendees") == []
    assert google.calls_of("send_email") == []


def test_already_queued_invites_drain_without_patching_calendar(
    session, programme, judging_session, participant_factory, google
):
    """Rows already in the outbox must complete without adding attendees."""
    from projet.models.enums import OutboxSubjectType
    from projet.outbox.effects import enqueue

    participant = participant_factory()
    enqueue(
        session,
        subject_type=OutboxSubjectType.PARTICIPANT,
        subject_id=participant.id,
        effect_type=JUDGING_SESSION_INVITE,
    )
    session.flush()
    run_once(session, google)

    row = session.scalar(select(Outbox))
    assert row.status == OutboxStatus.DONE
    assert row.result == {"skipped": True}
    assert google.calls_of("patch_event_attendees") == []


def test_a_queued_invite_with_no_session_is_skipped_not_retried(
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

    assert row.status == OutboxStatus.DONE
    assert row.result == {"skipped": True}
