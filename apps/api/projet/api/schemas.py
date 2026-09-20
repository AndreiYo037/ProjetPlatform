"""Response models, split by audience.

The split is the enforcement mechanism for section 8's privacy rule and FR-1004:
a participant-facing schema has no field to put a score in, so the rule holds by
construction rather than by remembering to omit it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from projet.services.branding import logo_url

ORM = ConfigDict(from_attributes=True)


class CompanySummary(BaseModel):
    model_config = ORM

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    website_url: str | None = None
    tier: str

    @model_validator(mode="after")
    def _render_logo(self) -> CompanySummary:
        """The column holds a storage key; the wire carries an address.

        Done here rather than at each call site so that every screen showing a
        company shows its logo, without anyone having to remember to convert it.
        """
        self.logo_url = logo_url(self.id, self.logo_url)
        return self


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
    slot: str
    name: str
    anchor_5: str | None = None
    anchor_3: str | None = None
    anchor_1: str | None = None
    is_universal: bool = False
    role_name: str | None = None

    @field_validator("slot", mode="before")
    @classmethod
    def _slot_as_label(cls, value: object) -> object:
        return str(value) if isinstance(value, int) else value


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
    kickoff_at: datetime | None = None
    # Same instant as submit_deadline_at (end of the last day). Carried on the
    # wire so the apply form can name both dates a participant is committing to.
    pitch_at: datetime | None = None
    pitch_starts_at: datetime | None = None
    pitch_duration_minutes: int | None = None
    kickoff_meet_link: str | None = None
    pitch_meet_link: str | None = None
    company: CompanySummary | None = None
    role: RoleSummary | None = None
    roles: list[RoleSummary] = []


class ProgrammeDetail(ProgrammeOut):
    brief_url: str | None = None
    problem_statement: str | None = None
    deliverable_spec: str | None = None
    requires_confidentiality_ack: bool = False
    criteria: list[CriterionOut] = []
    winners_count: int = 1
