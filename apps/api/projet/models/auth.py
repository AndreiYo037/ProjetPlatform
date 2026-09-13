"""Authentication: platform staff, passwords, one-time account tokens, sessions.

Email and password for all three actor types. Every account holds its own
credential; nothing depends on possessing an inbox to sign in day to day.

An `AccountActionToken` still exists, but only for the two moments a live
session cannot cover: setting a password on a freshly invited account, and
resetting a forgotten one. It is single-purpose and single-use, not a login
mechanism — the distinction that matters is that this token proves an email
was reachable *once*, at account setup, not that reachability is an ongoing
substitute for a credential.

Two security properties are load-bearing and enforced here rather than by
convention:
  * both passwords and tokens are stored hashed, so a leaked database row is
    not a login
  * sessions are database-backed rather than stateless, so a 30-day session
    (FR-012) can actually be revoked
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import AccountActionPurpose, ActorType, PlatformRole


class PlatformUser(Base):
    """Projet staff. Separate from CompanyUser on purpose.

    CompanyUser roles are all company-scoped; platform staff see across every
    company, which is a different kind of authority and wants a different table.
    """

    __tablename__ = "platform_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[PlatformRole] = mapped_column(
        enum_column(PlatformRole), default=PlatformRole.ADMIN
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class AccountActionToken(Base):
    """A one-time token for account setup or password reset — never for login.

    redirect_path preserves FR-013's deep-link behaviour where it still
    applies: a notification email can still carry a link straight to the
    relevant screen, it just authenticates through the session the person
    already holds rather than through the link itself.
    """

    __tablename__ = "account_action_token"
    __table_args__ = (Index("ix_account_action_token_subject", "actor_type", "subject_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType))
    subject_id: Mapped[uuid.UUID] = mapped_column()
    purpose: Mapped[AccountActionPurpose] = mapped_column(enum_column(AccountActionPurpose))
    email: Mapped[str] = mapped_column(String(320))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    redirect_path: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(TimestampTZ)
    consumed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    @property
    def is_usable(self) -> bool:
        return self.consumed_at is None and self.expires_at > utcnow()


class AuthSession(Base):
    """A signed-in device (FR-012 — 30 days).

    Database-backed rather than a stateless token so a session can be ended:
    thirty days is a long time to be unable to revoke access, and section 8
    requires company-user actions to be attributable.
    """

    __tablename__ = "auth_session"
    __table_args__ = (Index("ix_auth_session_subject", "actor_type", "subject_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType))
    subject_id: Mapped[uuid.UUID] = mapped_column()
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(400))
    expires_at: Mapped[datetime] = mapped_column(TimestampTZ)
    revoked_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    last_seen_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    @property
    def is_live(self) -> bool:
        return self.revoked_at is None and self.expires_at > utcnow()
