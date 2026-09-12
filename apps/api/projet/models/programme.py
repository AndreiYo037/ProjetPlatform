"""Events, programmes, judging sessions, rubric criteria and the data pack."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import JSONList, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import (
    DeliveryMode,
    ProgrammeStatus,
    Provenance,
    VerificationStatus,
)


class Event(Base):
    """Optional grouping — a hackathon weekend with several company tracks."""

    __tablename__ = "event"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    venue: Mapped[str | None] = mapped_column(String(300))
    starts_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    ends_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class Programme(Base):
    __tablename__ = "programme"
    __table_args__ = (
        UniqueConstraint("company_id", "slug"),
        CheckConstraint("team_size_max >= 1", name="team_size_max_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("event.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(160))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"))
    brief_url: Mapped[str | None] = mapped_column(Text)

    # FR-056a — null means no cap; admin admits by judgement.
    capacity: Mapped[int | None] = mapped_column(Integer)
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        enum_column(DeliveryMode), default=DeliveryMode.ONLINE
    )
    team_size_max: Mapped[int] = mapped_column(Integer, default=1)

    applications_open_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    applications_close_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    start_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    submit_deadline_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    status: Mapped[ProgrammeStatus] = mapped_column(
        enum_column(ProgrammeStatus), default=ProgrammeStatus.DRAFT
    )

    # Set by the deadline sweep so due work is claimed exactly once (FR-1500).
    deadline_processed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    winners_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    criteria: Mapped[list[RubricCriterion]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )
    judging_sessions: Mapped[list[JudgingSession]] = relationship(
        back_populates="programme", cascade="all, delete-orphan"
    )


class JudgingSession(Base):
    """Promoted from PRD section 4's inline judging_sessions[] array.

    Participant.judging_session_id needs an FK target, FR-811c needs a stored
    Calendar event id to patch, and FR-811b's session-length arithmetic needs a
    capacity per session.
    """

    __tablename__ = "judging_session"

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    starts_at: Mapped[datetime] = mapped_column(TimestampTZ)
    ends_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    location_or_meet_link: Mapped[str | None] = mapped_column(Text)
    google_event_id: Mapped[str | None] = mapped_column(String(300))
    capacity: Mapped[int | None] = mapped_column(Integer)

    programme: Mapped[Programme] = relationship(back_populates="judging_sessions")


class RubricCriterion(Base):
    """FR-071 — exactly four per programme, stored as data, never as code."""

    __tablename__ = "rubric_criterion"
    __table_args__ = (
        UniqueConstraint("programme_id", "slot"),
        CheckConstraint("slot between 1 and 4", name="slot_range"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    anchor_5: Mapped[str | None] = mapped_column(Text)
    anchor_3: Mapped[str | None] = mapped_column(Text)
    anchor_1: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    programme: Mapped[Programme] = relationship(back_populates="criteria")

    @property
    def is_universal(self) -> bool:
        """Slots 1 and 4 are fixed; they are what makes cohorts comparable."""
        return self.slot in (1, 4)

    @property
    def is_complete(self) -> bool:
        return bool(self.name and self.anchor_5 and self.anchor_3 and self.anchor_1)


class DataPackResource(Base):
    __tablename__ = "data_pack_resource"

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programme.id", ondelete="CASCADE")
    )
    # Registry entries seeded from a role template carry no programme.
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(300))
    url_or_storage_key: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(
        enum_column(Provenance), default=Provenance.PUBLIC
    )
    licence: Mapped[str | None] = mapped_column(String(200))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        enum_column(VerificationStatus), default=VerificationStatus.UNVERIFIED
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    access_status: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[list[str]] = mapped_column(JSONList, default=list)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("company_user.id"))
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
