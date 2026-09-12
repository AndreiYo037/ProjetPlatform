"""The outbox (FR-1300).

Deviation from PRD section 4, recorded in docs/decisions.md:
  * polymorphic subject, because offer and rejection emails fire while the
    subject is an Application and magic links belong to a CompanyUser
  * idempotency_key unique, which is what actually enforces FR-1303
  * next_attempt_at, because FR-1302's exponential backoff has nowhere else to live
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from projet.db import Base
from projet.models.base import JSONDict, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import OutboxStatus, OutboxSubjectType


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        Index("ix_outbox_due", "status", "next_attempt_at"),
        Index("ix_outbox_subject", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_type: Mapped[OutboxSubjectType] = mapped_column(enum_column(OutboxSubjectType))
    subject_id: Mapped[uuid.UUID] = mapped_column()
    # Kept as a convenience FK for the common case; not the idempotency key.
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participant.id", ondelete="SET NULL")
    )
    effect_type: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    payload: Mapped[dict] = mapped_column(JSONDict, default=dict)

    status: Mapped[OutboxStatus] = mapped_column(
        enum_column(OutboxStatus), default=OutboxStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    last_error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSONDict)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    @staticmethod
    def build_key(subject_type: OutboxSubjectType, subject_id: uuid.UUID, effect: str) -> str:
        return f"{subject_type.value}:{subject_id}:{effect}"
