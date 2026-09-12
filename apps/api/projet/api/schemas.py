"""Response models, split by audience.

The split is the enforcement mechanism for section 8's privacy rule and FR-1004:
a participant-facing schema has no field to put a score in, so the rule holds by
construction rather than by remembering to omit it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)


class CompanySummary(BaseModel):
    model_config = ORM

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    tier: str


class CompanyUserOut(BaseModel):
    model_config = ORM

    id: uuid.UUID
    name: str
    email: str
    title: str | None = None
    role: str
    status: str
    last_login_at: datetime | None = None


class CompanyUserInvite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320)
    title: str | None = Field(default=None, max_length=200)
    role: str = Field(default="rep")


class RoleSummary(BaseModel):
    model_config = ORM

    id: uuid.UUID
    name: str
    slug: str
    cluster: str
    aliases: list[str] = []


class RoleImplications(BaseModel):
    """FR-053 — what the company sees the moment they pick a role.

    This is where the programme stops being abstract for the buyer, and it
    prevents the common failure where a company picks a role whose deliverable
    is not what they actually wanted.
    """

    role: RoleSummary
    default_deliverable: str
    universal_memo: str | None = None
    public_sources: list[str]
    student_tools: list[str]
    judging_criteria: list[dict]
    company_asks_easy: list[str]
    delivery_risk_note: str | None = None


class CriterionOut(BaseModel):
    model_config = ORM

    id: uuid.UUID
    slot: int
    name: str
    anchor_5: str | None = None
    anchor_3: str | None = None
    anchor_1: str | None = None
    is_universal: bool = False


class ProgrammeOut(BaseModel):
    model_config = ORM

    id: uuid.UUID
    title: str
    slug: str
    status: str
    delivery_mode: str
    capacity: int | None = None
    team_size_max: int
    applications_open_at: datetime | None = None
    applications_close_at: datetime | None = None
    start_at: datetime | None = None
    submit_deadline_at: datetime | None = None
    company: CompanySummary | None = None
    role: RoleSummary | None = None


class ProgrammeDetail(ProgrammeOut):
    brief_url: str | None = None
    criteria: list[CriterionOut] = []
    winners_count: int = 1
