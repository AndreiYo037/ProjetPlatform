"""Role taxonomy, role templates and the skills taxonomy (FR-040, FR-903)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from projet.db import Base
from projet.models.base import JSONList, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import SkillStatus, SkillType


class Role(Base):
    """FR-041 — a controlled taxonomy, ~75 roles across 11 clusters."""

    __tablename__ = "role"

    id: Mapped[uuid.UUID] = uuid_pk()
    cluster: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(160), unique=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    aliases: Mapped[list[str]] = mapped_column(JSONList, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[RoleTemplate | None] = relationship(
        back_populates="role", uselist=False, cascade="all, delete-orphan"
    )


class RoleTemplate(Base):
    """FR-042 — everything that can be pre-built for a role.

    Three fields beyond PRD section 4, each carrying content that exists in the
    seed documents and had nowhere to live: student_tools, delivery_risk_note,
    and public_sources as structured entries rather than bare strings.
    """

    __tablename__ = "role_template"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )
    default_deliverable: Mapped[str] = mapped_column(Text)
    public_sources: Mapped[list[dict]] = mapped_column(JSONList, default=list)
    student_tools: Mapped[list[str]] = mapped_column(JSONList, default=list)
    asks_easy: Mapped[list[str]] = mapped_column(JSONList, default=list)
    asks_moderate: Mapped[list[str]] = mapped_column(JSONList, default=list)
    asks_hard: Mapped[list[str]] = mapped_column(JSONList, default=list)

    rubric_slot2_name: Mapped[str] = mapped_column(String(160))
    rubric_slot2_anchor_5: Mapped[str] = mapped_column(Text)
    rubric_slot2_anchor_3: Mapped[str] = mapped_column(Text)
    rubric_slot2_anchor_1: Mapped[str] = mapped_column(Text)
    rubric_slot3_name: Mapped[str] = mapped_column(String(160))
    rubric_slot3_anchor_5: Mapped[str] = mapped_column(Text)
    rubric_slot3_anchor_3: Mapped[str] = mapped_column(Text)
    rubric_slot3_anchor_1: Mapped[str] = mapped_column(Text)

    ranked_hard_skills: Mapped[list[str]] = mapped_column(JSONList, default=list)
    ranked_soft_skills: Mapped[list[str]] = mapped_column(JSONList, default=list)

    delivery_risk_note: Mapped[str | None] = mapped_column(Text)

    role: Mapped[Role] = relationship(back_populates="template")


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160), unique=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    type: Mapped[SkillType] = mapped_column(enum_column(SkillType))
    aliases: Mapped[list[str]] = mapped_column(JSONList, default=list)
    status: Mapped[SkillStatus] = mapped_column(
        enum_column(SkillStatus), default=SkillStatus.CANONICAL
    )
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
