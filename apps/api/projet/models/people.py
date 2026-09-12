"""Person, Application, Participant and Team.

Person is separate from Application deliberately: a returning participant
applies to a second programme against the same Person record and their profile
accumulates. Get this wrong and the profile never compounds.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import ApplicationStatus, OrgType, ParticipantStatus


def normalise_email(value: str | None) -> str | None:
    return value.strip().lower() if value else None


class Person(Base):
    __tablename__ = "person"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[str] = mapped_column(String(320))
    google_email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(60))
    organisation: Mapped[str | None] = mapped_column(String(300))
    org_type: Mapped[OrgType | None] = mapped_column(enum_column(OrgType))
    year_course: Mapped[str | None] = mapped_column(String(300))
    job_title: Mapped[str | None] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Singapore")
    # FR-1201 — the public profile lives at /p/{handle}. Scheme still open
    # (PRD section 12 question 1); the column existing now keeps it out of a migration.
    handle: Mapped[str | None] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


# Case-insensitive identity: one human, one Person, across every programme.
# Declared after the class so it can reference the mapped column expression.
Index(
    "ix_person_contact_email_lower",
    func.lower(Person.contact_email),
    unique=True,
)


class Application(Base):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("programme_id", "person_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    cv_url: Mapped[str | None] = mapped_column(Text)
    writeup: Mapped[str | None] = mapped_column(Text)

    # FR-203 — stored with a timestamp, immutably.
    consent_share_company: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_captured_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    score_relevance: Mapped[int | None] = mapped_column(Integer)
    score_specificity: Mapped[int | None] = mapped_column(Integer)
    score_capability: Mapped[int | None] = mapped_column(Integer)
    score_followthrough: Mapped[int | None] = mapped_column(Integer)
    score_total: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus), default=ApplicationStatus.SUBMITTED
    )
    offer_token: Mapped[str | None] = mapped_column(String(128), unique=True)
    offer_sent_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    offer_expires_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    rejection_feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    person: Mapped[Person] = relationship()


class Participant(Base):
    __tablename__ = "participant"
    __table_args__ = (UniqueConstraint("programme_id", "person_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id"))
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    gmail_thread_id: Mapped[str | None] = mapped_column(String(120))

    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded_reason: Mapped[str | None] = mapped_column(Text)

    # FR-811b — assigned at acceptance, not after the deadline.
    run_order: Mapped[int | None] = mapped_column(Integer)
    judging_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("judging_session.id", ondelete="SET NULL")
    )

    attended_kickoff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[ParticipantStatus] = mapped_column(
        enum_column(ParticipantStatus), default=ParticipantStatus.CONFIRMED
    )
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    person: Mapped[Person] = relationship()
    application: Mapped[Application] = relationship()


class Team(Base):
    """One row per solo participant too, so submissions always resolve
    through a team and hackathon pairs need no retrofit."""

    __tablename__ = "team"

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    members: Mapped[list[TeamMember]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    __tablename__ = "team_member"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE"), primary_key=True
    )

    team: Mapped[Team] = relationship(back_populates="members")
    participant: Mapped[Participant] = relationship()
