"""Authentication: platform staff, magic-link tokens and sessions.

One mechanism for all three actor types (FR-011). A rep opening the scoring
screen ninety seconds before a pitch will not reset a password, and a
participant fitting this around classes will not remember one either.

Two security properties are load-bearing and enforced here rather than by
convention:
  * tokens are stored as SHA-256 hashes, so a leaked database row is not a login
  * sessions are database-backed rather than stateless, so a 30-day session
    (FR-012) can actually be revoked
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import ActorType, PlatformRole


class PlatformUser(Base):
    """Projet staff. Separate from CompanyUser on purpose.

    CompanyUser roles are all company-scoped; platform staff see across every
    company, which is a different kind of authority and wants a different table.
    """

    __tablename__ = "platform_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    role: Mapped[PlatformRole] = mapped_column(
        enum_column(PlatformRole), default=PlatformRole.ADMIN
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class MagicLinkToken(Base):
    """FR-011/FR-013 — single-use, expiring, deep-linkable.

    redirect_path is what makes FR-013 work: a rep clicking "score now" from
    their inbox lands on the candidate card already signed in, rather than on a
    sign-in screen that then forgets where they were going.
    """

    __tablename__ = "magic_link_token"
    __table_args__ = (Index("ix_magic_link_token_subject", "actor_type", "subject_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType))
    subject_id: Mapped[uuid.UUID] = mapped_column()
    email: Mapped[str] = mapped_column(String(320))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    redirect_path: Mapped[str | None] = mapped_column(Text)
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
