"""Project entries: the work itself, verified and self-declared side by side.

A profile that only holds what this platform watched is a profile with one
programme on it. Most people arrive with a hackathon, an internship and a
side project already behind them, and refusing to carry those makes the page
useless to the person it belongs to.

So both live here, in one table, told apart by one column:

    participant_id set   -> verified. The associated experience and the dates
                            came from a programme this platform ran. The
                            description is still theirs.
    participant_id null  -> self-declared. Every word is theirs.

The distinction is never collapsed. It drives ordering (verified first) and
two separate counts, so self-declared volume can never read as evidence.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import ArtifactVisibility
from projet.models.taxonomy import Skill


class ProjectEntry(Base):
    """One project card."""

    __tablename__ = "project_entry"
    __table_args__ = (
        # A programme yields one entry, not one per time the seed is clicked.
        UniqueConstraint("participant_id", name="uq_project_entry_participant"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))

    # Null means self-declared. Set means the facts below came from a
    # programme this platform ran, and stay out of the participant's reach.
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participant.id", ondelete="SET NULL")
    )

    title: Mapped[str] = mapped_column(String(300))
    # The job, course or programme this sat under. Free text: there is no
    # experience or education record on a profile yet to point at.
    associated_experience: Mapped[str | None] = mapped_column(String(300))

    started_at: Mapped[date | None] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    # Distinct from "no end date recorded", which is what a null ended_at
    # means on its own — a card should be able to say it is still running.
    ongoing: Mapped[bool] = mapped_column(Boolean, default=False)

    # The problem, what they did about it, and what came of it — one field,
    # because a case study reads as prose and four boxes made it a form.
    # Authored by the participant in every case: a verified entry verifies
    # who they worked for, not their account of it.
    description: Mapped[str | None] = mapped_column(Text)

    # Per-project and defaulting closed. A data pack a company shared under
    # confidentiality is never reachable through this, whatever is set here.
    artifact_visibility: Mapped[ArtifactVisibility] = mapped_column(
        enum_column(ArtifactVisibility), default=ArtifactVisibility.PRIVATE
    )

    # Within a verified/self-declared band. Verified always sorts ahead.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    links: Mapped[list[ProjectLink]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    skills: Mapped[list[ProjectSkill]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    @property
    def verified(self) -> bool:
        return self.participant_id is not None


class ProjectLink(Base):
    """Where the work is: a URL somewhere else, or a file they uploaded.

    One table for both because they are the same thing to a reader — the work
    itself — and gating them separately would mean two places to get the
    consent check right instead of one.
    """

    __tablename__ = "project_link"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_entry.id", ondelete="CASCADE")
    )

    # Exactly one of these is set. A URL points off-platform; a storage key
    # points at an uploaded file, which is never publicly addressable and is
    # served through an expiring signed link (section 8).
    url: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(String(400))
    filename: Mapped[str | None] = mapped_column(String(300))
    content_type: Mapped[str | None] = mapped_column(String(120))

    label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    entry: Mapped[ProjectEntry] = relationship(back_populates="links")

    @property
    def is_file(self) -> bool:
        return self.storage_key is not None


class ProjectSkill(Base):
    """A skill claimed on a self-declared project.

    The self-declared counterpart to ProfileSkill, and a separate table rather
    than a nullable programme_id on that one. ProfileSkill rows carry an
    attester; these carry nobody. Keeping them in different tables means a
    query for attested evidence cannot accidentally sweep up a claim, which a
    nullable column would make a matter of remembering a WHERE clause.
    """

    __tablename__ = "project_skill"
    __table_args__ = (UniqueConstraint("project_entry_id", "skill_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_entry.id", ondelete="CASCADE")
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skill.id"))

    entry: Mapped[ProjectEntry] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()
