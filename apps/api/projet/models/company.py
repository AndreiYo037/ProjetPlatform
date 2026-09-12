"""Companies, their users, programme scoping and magic-link tokens (FR-010)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import JSONDict, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import CompanyTier, CompanyUserRole, CompanyUserStatus


class Company(Base):
    __tablename__ = "company"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    tier: Mapped[CompanyTier] = mapped_column(enum_column(CompanyTier), default=CompanyTier.SME)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    users: Mapped[list[CompanyUser]] = relationship(back_populates="company")


class CompanyUser(Base):
    __tablename__ = "company_user"
    __table_args__ = (UniqueConstraint("company_id", "email"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    title: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[CompanyUserRole] = mapped_column(enum_column(CompanyUserRole))
    status: Mapped[CompanyUserStatus] = mapped_column(
        enum_column(CompanyUserStatus), default=CompanyUserStatus.INVITED
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("company_user.id"))
    last_login_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="users")


class ProgrammeAssignment(Base):
    """FR-015 — a rep sees only the programmes they are assigned to."""

    __tablename__ = "programme_assignment"

    programme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programme.id", ondelete="CASCADE"), primary_key=True
    )
    company_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_user.id", ondelete="CASCADE"), primary_key=True
    )
    can_score: Mapped[bool] = mapped_column(Boolean, default=True)


class MagicLinkToken(Base):
    """FR-011/FR-013 — single-use, expiring, deep-linkable.

    Tokens are stored hashed: a leaked database row must not be a usable login.
    """

    __tablename__ = "magic_link_token"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_user.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    redirect_path: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(TimestampTZ)
    consumed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class AuditLog(Base):
    """Section 8 — admin and company-user actions are logged.

    Not in PRD section 4; the non-functional requirement has nowhere else to land.
    """

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_subject", "subject_type", "subject_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(120))
    subject_type: Mapped[str] = mapped_column(String(60))
    subject_id: Mapped[uuid.UUID | None] = mapped_column()
    detail: Mapped[dict | None] = mapped_column(JSONDict)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
