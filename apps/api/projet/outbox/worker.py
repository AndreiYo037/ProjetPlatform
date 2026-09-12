"""The outbox worker.

Claiming uses FOR UPDATE SKIP LOCKED on Postgres so several workers can run;
SQLite has no such thing, and the test suite is single-threaded, so it falls
back to a plain ordered read.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.config import get_settings
from projet.db import get_sessionmaker
from projet.integrations.google.client import (
    GoogleClient,
    PermanentGoogleError,
    TransientGoogleError,
    get_google_client,
)
from projet.models import Outbox
from projet.models.base import utcnow
from projet.models.enums import OutboxStatus
from projet.outbox.effects import (
    EffectContext,
    PermanentEffectError,
    TransientEffectError,
    registry,
)

log = logging.getLogger(__name__)


def backoff_delay(attempts: int) -> timedelta:
    """30s, 60s, 120s, 240s, 480s — long enough to outlast a blip, short enough
    that a deadline-night failure is still recoverable."""
    base = get_settings().outbox_backoff_base_seconds
    return timedelta(seconds=base * (2 ** max(0, attempts - 1)))


def claim_due(session: Session, limit: int = 20) -> list[Outbox]:
    statement = (
        select(Outbox)
        .where(Outbox.status == OutboxStatus.PENDING)
        .where(Outbox.next_attempt_at <= utcnow())
        .order_by(Outbox.next_attempt_at)
        .limit(limit)
    )
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    return list(session.scalars(statement))


def execute_one(session: Session, row: Outbox, google: GoogleClient) -> None:
    """Run one effect and record what happened. Never raises."""
    settings = get_settings()
    handler = registry.get(row.effect_type)
    row.attempts += 1

    if handler is None:
        row.status = OutboxStatus.FAILED
        row.last_error = f"no handler registered for effect {row.effect_type!r}"
        row.completed_at = utcnow()
        return

    try:
        result = handler(EffectContext(session=session, google=google, row=row))
    except (PermanentEffectError, PermanentGoogleError) as error:
        row.status = OutboxStatus.FAILED
        row.last_error = f"permanent: {error}"
        row.completed_at = utcnow()
        log.warning("outbox %s permanently failed: %s", row.effect_type, error)
    except (TransientEffectError, TransientGoogleError) as error:
        row.last_error = f"transient: {error}"
        if row.attempts >= settings.outbox_max_attempts:
            row.status = OutboxStatus.FAILED
            row.completed_at = utcnow()
            log.error("outbox %s exhausted retries: %s", row.effect_type, error)
        else:
            row.next_attempt_at = utcnow() + backoff_delay(row.attempts)
    except Exception as error:  # unexpected: treat as transient, but record loudly
        row.last_error = f"unexpected: {error!r}"
        if row.attempts >= settings.outbox_max_attempts:
            row.status = OutboxStatus.FAILED
            row.completed_at = utcnow()
        else:
            row.next_attempt_at = utcnow() + backoff_delay(row.attempts)
        log.exception("outbox %s raised unexpectedly", row.effect_type)
    else:
        row.status = OutboxStatus.DONE
        row.result = result or {}
        row.completed_at = utcnow()
        row.last_error = None


def run_once(session: Session, google: GoogleClient | None = None, limit: int = 20) -> int:
    """Execute all due effects. Returns how many were attempted."""
    client = google or get_google_client()
    rows = claim_due(session, limit=limit)
    for row in rows:
        execute_one(session, row, client)
    session.commit()
    return len(rows)


def health(session: Session) -> dict[str, int]:
    """FR-1304 — pending, failed, stuck. 'Stuck' means pending, overdue, and
    already retried, which is the shape of a problem rather than a queue."""
    from sqlalchemy import func

    counts: dict[OutboxStatus, int] = {
        status: count
        for status, count in session.execute(
            select(Outbox.status, func.count()).group_by(Outbox.status)
        ).all()
    }
    stuck = session.scalar(
        select(func.count())
        .select_from(Outbox)
        .where(Outbox.status == OutboxStatus.PENDING)
        .where(Outbox.attempts > 0)
        .where(Outbox.next_attempt_at <= utcnow())
    )
    return {
        "pending": counts.get(OutboxStatus.PENDING, 0),
        "done": counts.get(OutboxStatus.DONE, 0),
        "failed": counts.get(OutboxStatus.FAILED, 0),
        "stuck": stuck or 0,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with get_sessionmaker()() as session:
        attempted = run_once(session)
        log.info("outbox sweep attempted %d effect(s)", attempted)
