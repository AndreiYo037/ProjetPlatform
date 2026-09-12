"""Participant-supplied Drive links, validated on paste and snapshotted at the
deadline (FR-800).

The snapshot is the requirement that makes Drive links workable: locking the
link field does not lock the document, so what the judge sees is the frozen copy.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import AccessStatus, SnapshotStatus, SubmissionSlot, SubmissionStatus


class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = (UniqueConstraint("team_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"))
    status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus), default=SubmissionStatus.DRAFT
    )
    submitted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    locked_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    links: Mapped[list[SubmissionLink]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )

    @property
    def is_complete(self) -> bool:
        """FR-802 — cannot be complete while any link fails to open."""
        return bool(self.links) and all(
            link.access_status == AccessStatus.OK for link in self.links
        )


class SubmissionLink(Base):
    __tablename__ = "submission_link"
    __table_args__ = (UniqueConstraint("submission_id", "slot"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submission.id", ondelete="CASCADE")
    )
    slot: Mapped[SubmissionSlot] = mapped_column(enum_column(SubmissionSlot))
    drive_url: Mapped[str | None] = mapped_column(Text)
    drive_file_id: Mapped[str | None] = mapped_column(String(200))
    detected_filename: Mapped[str | None] = mapped_column(String(400))
    detected_mime: Mapped[str | None] = mapped_column(String(200))

    access_status: Mapped[AccessStatus] = mapped_column(
        enum_column(AccessStatus), default=AccessStatus.UNCHECKED
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    snapshot_key: Mapped[str | None] = mapped_column(Text)
    snapshot_mime: Mapped[str | None] = mapped_column(String(200))
    snapshot_bytes: Mapped[int | None] = mapped_column(Integer)
    snapshot_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    snapshot_status: Mapped[SnapshotStatus] = mapped_column(
        enum_column(SnapshotStatus), default=SnapshotStatus.PENDING
    )

    submission: Mapped[Submission] = relationship(back_populates="links")
