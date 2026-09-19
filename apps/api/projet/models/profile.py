"""The durable product: credentials, judge-attested skills, testimonials."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import CredentialType


class Credential(Base):
    __tablename__ = "credential"
    __table_args__ = (UniqueConstraint("person_id", "programme_id", "type"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    type: Mapped[CredentialType] = mapped_column(enum_column(CredentialType))
    verify_code: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class ProfileSkill(Base):
    """FR-903d — judge-attested, not self-declared. The attestation carries the
    name, title and company of the practitioner who tagged it, which is what
    makes it materially stronger than a self-reported skill."""

    __tablename__ = "profile_skill"
    __table_args__ = (UniqueConstraint("person_id", "programme_id", "skill_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skill.id"))
    attested_by_name: Mapped[str | None] = mapped_column(String(200))
    attested_by_title: Mapped[str | None] = mapped_column(String(200))
    attested_by_company: Mapped[str | None] = mapped_column(String(200))
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class Testimonial(Base):
    """FR-1053 — authored on the submissions dashboard, with no link to Score."""

    __tablename__ = "testimonial"

    id: Mapped[uuid.UUID] = uuid_pk()
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE")
    )
    author_company_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_user.id"))
    body: Mapped[str] = mapped_column(Text)
    # The signed letter. Drafting fills `body`; publishing requires this file.
    pdf_storage_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
