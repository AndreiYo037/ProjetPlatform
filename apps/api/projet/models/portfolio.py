"""Case-study entries: the work itself, verified and self-declared side by side.

A profile that only holds what this platform watched is a profile with one
programme on it. Most people arrive with a hackathon, an internship and a
side project already behind them, and refusing to carry those makes the page
useless to the person it belongs to.

So both live here, in one table, structurally distinguished by one column:

    participant_id set   -> verified. The organisation, the dates and the
                            attested skills come from a programme this
                            platform ran. The narrative is still theirs.
    participant_id null  -> self-declared. Every word is theirs.

The distinction is never collapsed. It drives ordering (verified first), it
drives two separate counts on the profile, and it is what stops volume of
self-declared work reading as weight of evidence.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import JSONList, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import ArtifactVisibility, ProjectKind, ProjectLinkKind


class ProjectEntry(Base):
    """One case-study card."""

    __tablename__ = "project_entry"
    __table_args__ = (
        # A programme yields one entry, not one per time the seed is clicked.
        UniqueConstraint("participant_id", name="uq_project_entry_participant"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))

    # Null means self-declared. Set means the facts below were derived from a
    # programme this platform ran, and stay out of the participant's reach.
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participant.id", ondelete="SET NULL")
    )

    kind: Mapped[ProjectKind] = mapped_column(enum_column(ProjectKind))
    title: Mapped[str] = mapped_column(String(300))
    organisation_name: Mapped[str | None] = mapped_column(String(300))
    started_at: Mapped[date | None] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)

    # The four beats of a case study. Authored by the participant in every
    # case — a verified entry verifies who they worked for and what was
    # observed, not their account of it.
    problem: Mapped[str | None] = mapped_column(Text)
    approach: Mapped[str | None] = mapped_column(Text)
    contribution: Mapped[list[str]] = mapped_column(JSONList, default=list)
    outcome: Mapped[str | None] = mapped_column(Text)

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
    """Where the work actually is."""

    __tablename__ = "project_link"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_entry.id", ondelete="CASCADE")
    )
    kind: Mapped[ProjectLinkKind] = mapped_column(enum_column(ProjectLinkKind))
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)

    entry: Mapped[ProjectEntry] = relationship(back_populates="links")


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
