"""Programme channel, direct threads, posts and read state (FR-600)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import AuthorRole, ThreadStatus, ThreadType


class Thread(Base):
    __tablename__ = "thread"

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id", ondelete="CASCADE"))
    type: Mapped[ThreadType] = mapped_column(enum_column(ThreadType))
    title: Mapped[str | None] = mapped_column(String(400))
    author_id: Mapped[uuid.UUID | None] = mapped_column()
    author_role: Mapped[AuthorRole] = mapped_column(enum_column(AuthorRole))
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned_until: Mapped[datetime | None] = mapped_column(TimestampTZ)
    status: Mapped[ThreadStatus] = mapped_column(
        enum_column(ThreadStatus), default=ThreadStatus.OPEN
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("thread.id", ondelete="SET NULL")
    )
    requires_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    posts: Mapped[list[Post]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class ThreadMember(Base):
    """Populated only for direct threads."""

    __tablename__ = "thread_member"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("thread.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_role: Mapped[AuthorRole] = mapped_column(enum_column(AuthorRole))


class Post(Base):
    __tablename__ = "post"

    id: Mapped[uuid.UUID] = uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("thread.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID | None] = mapped_column()
    author_role: Mapped[AuthorRole] = mapped_column(enum_column(AuthorRole))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    edited_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    # FR-613 — removals leave a visible tombstone rather than vanishing.
    removed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    thread: Mapped[Thread] = relationship(back_populates="posts")
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[uuid.UUID] = uuid_pk()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(400))
    storage_key: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    post: Mapped[Post] = relationship(back_populates="attachments")


class ThreadRead(Base):
    """Drives unread counts and acknowledgement tracking."""

    __tablename__ = "thread_read"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("thread.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
