"""The effect registry.

The provisioning chain (FR-1400) is several external calls in a row. If a
Calendar patch succeeds and the next step times out, the retry must not fire
the already-done step again — so each step is its own outbox row with its own
idempotency key, and the chain is declarative rather than one long function.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.integrations.google.client import GoogleClient
from projet.models import Outbox
from projet.models.enums import OutboxSubjectType


class EffectError(RuntimeError):
    pass


class TransientEffectError(EffectError):
    """Retry with backoff."""


class PermanentEffectError(EffectError):
    """Retrying cannot help; fail the row now rather than burning four attempts."""


@dataclass
class EffectContext:
    session: Session
    google: GoogleClient
    row: Outbox

    @property
    def payload(self) -> dict[str, Any]:
        return self.row.payload or {}


EffectHandler = Callable[[EffectContext], dict | None]
registry: dict[str, EffectHandler] = {}


def effect(name: str) -> Callable[[EffectHandler], EffectHandler]:
    def decorator(handler: EffectHandler) -> EffectHandler:
        if name in registry:
            raise RuntimeError(f"effect {name!r} already registered")
        registry[name] = handler
        return handler

    return decorator


def enqueue(
    session: Session,
    *,
    subject_type: OutboxSubjectType,
    subject_id: uuid.UUID,
    effect_type: str,
    payload: dict | None = None,
    participant_id: uuid.UUID | None = None,
    key_suffix: str | None = None,
) -> Outbox:
    """Write the intent. Idempotent on (subject, effect): asking twice for the
    same effect returns the existing row rather than queuing a second send.

    `key_suffix` is for effects that can honestly fire more than once on the
    same subject — a second testimonial, a later profile edit — without
    colliding with the first send.
    """
    key = Outbox.build_key(subject_type, subject_id, effect_type)
    if key_suffix:
        key = f"{key}:{key_suffix}"
    existing = session.scalar(select(Outbox).where(Outbox.idempotency_key == key))
    if existing is not None:
        return existing

    row = Outbox(
        subject_type=subject_type,
        subject_id=subject_id,
        participant_id=participant_id,
        effect_type=effect_type,
        idempotency_key=key,
        payload=payload or {},
    )
    session.add(row)
    session.flush()
    return row
