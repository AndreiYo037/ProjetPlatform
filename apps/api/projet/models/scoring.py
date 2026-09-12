"""Pitch scoring (FR-900).

Criterion scores attach to the team; skills tagging and the referral verdict are
captured per member, so a pair can produce one strong submission and two
different verdicts on the individuals (FR-909).

Nothing in this module is ever served to a participant-role session.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import ReferralIntent, ScorerType


class Score(Base):
    __tablename__ = "score"
    __table_args__ = (UniqueConstraint("team_id", "scorer_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"))
    scorer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_user.id"))
    scorer_type: Mapped[ScorerType] = mapped_column(enum_column(ScorerType), default=ScorerType.REP)
    total: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow, onupdate=utcnow)

    criterion_scores: Mapped[list[CriterionScore]] = relationship(
        back_populates="score", cascade="all, delete-orphan"
    )
    members: Mapped[list[ScoreMember]] = relationship(
        back_populates="score", cascade="all, delete-orphan"
    )


class CriterionScore(Base):
    __tablename__ = "criterion_score"
    __table_args__ = (
        UniqueConstraint("score_id", "criterion_id"),
        CheckConstraint("value between 1 and 5", name="value_range"),
    )

    score_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("score.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rubric_criterion.id"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer)

    score: Mapped[Score] = relationship(back_populates="criterion_scores")


class ScoreMember(Base):
    """Referral intent is per person even when the submission is joint.
    Never visible to participants (FR-904b)."""

    __tablename__ = "score_member"

    score_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("score.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE"), primary_key=True
    )
    would_refer: Mapped[ReferralIntent | None] = mapped_column(enum_column(ReferralIntent))

    score: Mapped[Score] = relationship(back_populates="members")


class ScoreSkillTag(Base):
    """FR-903 — what a judge observed, per participant."""

    __tablename__ = "score_skill_tag"

    score_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("score.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
