"""Outbox semantics (FR-1300).

The failure this prevents is concrete: provisioning sends a welcome email, then
Calendar times out. The retry must not send a second welcome email.
"""

from __future__ import annotations

import uuid

import pytest

from projet.config import get_settings
from projet.integrations.google.client import PermanentGoogleError, TransientGoogleError
from projet.models import Outbox
from projet.models.base import utcnow
from projet.models.enums import OutboxStatus, OutboxSubjectType
from projet.outbox.effects import (
    EffectContext,
    PermanentEffectError,
    TransientEffectError,
    effect,
    enqueue,
    registry,
)
from projet.outbox.worker import backoff_delay, health, run_once


@pytest.fixture
def effects():
    """Register throwaway effects and clean the registry afterwards."""
    names: list[str] = []

    def register(name, handler):
        names.append(name)
        effect(name)(handler)
        return name

    yield register
    for name in names:
        registry.pop(name, None)


def _enqueue(session, effect_type, subject_id=None, payload=None):
    return enqueue(
        session,
        subject_type=OutboxSubjectType.PARTICIPANT,
        subject_id=subject_id or uuid.uuid4(),
        effect_type=effect_type,
        payload=payload or {},
    )


def test_enqueue_is_idempotent_on_subject_and_effect(session):
    subject = uuid.uuid4()
    first = _enqueue(session, "some_effect", subject)
    second = _enqueue(session, "some_effect", subject)

    assert first.id == second.id
    assert session.query(Outbox).count() == 1


def test_a_replayed_effect_does_not_send_twice(session, google, effects):
    sends: list[str] = []

    def handler(ctx: EffectContext) -> dict:
        sends.append(str(ctx.row.subject_id))
        return {"sent": True}

    effects("send_once", handler)
    subject = uuid.uuid4()
    _enqueue(session, "send_once", subject)
    run_once(session, google)

    # Ask for the same effect again, as a re-run of the provisioning chain would.
    _enqueue(session, "send_once", subject)
    run_once(session, google)

    assert len(sends) == 1, "the same effect must not execute twice"


def test_transient_failure_retries_with_backoff(session, google, effects):
    attempts = {"count": 0}

    def handler(ctx: EffectContext) -> dict:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TransientEffectError("calendar timed out")
        return {"ok": True}

    effects("flaky", handler)
    row = _enqueue(session, "flaky")
    run_once(session, google)

    assert row.status == OutboxStatus.PENDING
    assert row.attempts == 1
    assert row.next_attempt_at > utcnow()

    # Pretend the backoff elapsed.
    row.next_attempt_at = utcnow()
    session.flush()
    run_once(session, google)

    assert row.status == OutboxStatus.DONE
    assert attempts["count"] == 2


def test_permanent_failure_stops_at_one_attempt(session, google, effects):
    attempts = {"count": 0}

    def handler(ctx: EffectContext) -> dict:
        attempts["count"] += 1
        raise PermanentEffectError("participant no longer exists")

    effects("doomed", handler)
    row = _enqueue(session, "doomed")
    run_once(session, google)

    assert row.status == OutboxStatus.FAILED
    assert row.attempts == 1, "retrying a permanent failure only delays the alert"
    assert "permanent" in (row.last_error or "")


def test_transient_failure_exhausts_retries_and_fails(session, google, effects):
    def handler(ctx: EffectContext) -> dict:
        raise TransientEffectError("still down")

    effects("always_down", handler)
    row = _enqueue(session, "always_down")

    for _ in range(get_settings().outbox_max_attempts):
        row.next_attempt_at = utcnow()
        session.flush()
        run_once(session, google)

    assert row.status == OutboxStatus.FAILED
    assert row.attempts == get_settings().outbox_max_attempts


def test_google_errors_map_onto_the_same_split(session, google, effects):
    def transient(ctx: EffectContext) -> dict:
        raise TransientGoogleError("429 rateLimitExceeded")

    def permanent(ctx: EffectContext) -> dict:
        raise PermanentGoogleError("404 notFound")

    effects("g_transient", transient)
    effects("g_permanent", permanent)
    t_row = _enqueue(session, "g_transient")
    p_row = _enqueue(session, "g_permanent")
    run_once(session, google)

    assert t_row.status == OutboxStatus.PENDING
    assert p_row.status == OutboxStatus.FAILED


def test_unregistered_effect_fails_loudly_rather_than_looping(session, google):
    row = _enqueue(session, "effect_that_does_not_exist")
    run_once(session, google)

    assert row.status == OutboxStatus.FAILED
    assert "no handler" in (row.last_error or "")


def test_backoff_is_exponential():
    delays = [backoff_delay(n).total_seconds() for n in range(1, 6)]
    assert delays == sorted(delays)
    assert delays[-1] > delays[0] * 4


def test_health_reports_pending_failed_and_stuck(session, google, effects):
    def handler(ctx: EffectContext) -> dict:
        raise TransientEffectError("down")

    effects("stuck_effect", handler)
    row = _enqueue(session, "stuck_effect")
    run_once(session, google)
    row.next_attempt_at = utcnow()
    session.flush()

    counts = health(session)
    assert counts["pending"] == 1
    assert counts["stuck"] == 1


def test_outbox_subject_can_be_an_application_not_only_a_participant(session):
    """The deviation from PRD section 4 exists because offer and rejection
    emails fire before a Participant exists at all."""
    row = enqueue(
        session,
        subject_type=OutboxSubjectType.APPLICATION,
        subject_id=uuid.uuid4(),
        effect_type="offer_email",
    )
    assert row.participant_id is None
    assert row.idempotency_key.startswith("application:")
