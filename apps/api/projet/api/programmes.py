"""Programme setup, rubric authoring and the data pack (FR-050, FR-060, FR-070)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import (
    get_programme_or_404,
    require_company_manager,
    require_platform,
    visible_programmes,
)
from projet.api.schemas import (
    CompanySummary,
    CriterionOut,
    ProgrammeDetail,
    ProgrammeOut,
    RoleSummary,
)
from projet.db import get_session
from projet.models import (
    Company,
    DataPackResource,
    JudgingSession,
    ProblemStatementDraft,
    Programme,
    Role,
    RubricCriterion,
)
from projet.models.base import utcnow
from projet.models.enums import DeliveryMode, ProgrammeStatus, Provenance, VerificationStatus
from projet.services.auth import Actor
from projet.services.rubric import (
    RubricError,
    compose_rubric,
    edit_criterion,
    publish,
    validate_for_publication,
)

router = APIRouter(tags=["programmes"])


class ProgrammeCreate(BaseModel):
    company_id: uuid.UUID
    role_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(min_length=1, max_length=160)
    delivery_mode: str = DeliveryMode.ONLINE.value
    capacity: int | None = None
    team_size_max: int = 1
    applications_open_at: datetime | None = None
    applications_close_at: datetime | None = None
    start_at: datetime | None = None
    submit_deadline_at: datetime | None = None
    winners_count: int = 1


class ProgrammeUpdate(BaseModel):
    title: str | None = None
    brief_url: str | None = None
    capacity: int | None = None
    team_size_max: int | None = None
    applications_open_at: datetime | None = None
    applications_close_at: datetime | None = None
    start_at: datetime | None = None
    submit_deadline_at: datetime | None = None
    winners_count: int | None = None


class CriterionUpdate(BaseModel):
    name: str | None = None
    anchor_5: str | None = None
    anchor_3: str | None = None
    anchor_1: str | None = None


class JudgingSessionCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime | None = None
    location_or_meet_link: str | None = None
    capacity: int | None = Field(
        default=12,
        description="Twelve pitches is a comfortable evening; thirty is four hours.",
    )


class DataPackResourceCreate(BaseModel):
    label: str = Field(min_length=1, max_length=300)
    url_or_storage_key: str | None = None
    provenance: str = Provenance.COMPANY_SUPPLIED.value
    licence: str | None = None


def _detail(db: Session, programme: Programme) -> ProgrammeDetail:
    data = ProgrammeDetail.model_validate(programme)
    company = db.get(Company, programme.company_id)
    role = db.get(Role, programme.role_id)
    if company:
        data.company = CompanySummary.model_validate(company)
    if role:
        data.role = RoleSummary.model_validate(role)
    criteria = db.scalars(
        select(RubricCriterion)
        .where(RubricCriterion.programme_id == programme.id)
        .order_by(RubricCriterion.slot)
    )
    data.criteria = [
        CriterionOut(
            id=c.id,
            slot=c.slot,
            name=c.name,
            anchor_5=c.anchor_5,
            anchor_3=c.anchor_3,
            anchor_1=c.anchor_1,
            is_universal=c.is_universal,
        )
        for c in criteria
    ]
    return data


@router.get("/programmes", response_model=list[ProgrammeOut])
def list_programmes(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> list[ProgrammeOut]:
    programmes = db.scalars(visible_programmes(db, actor).order_by(Programme.created_at.desc()))
    out = []
    for programme in programmes:
        item = ProgrammeOut.model_validate(programme)
        role = db.get(Role, programme.role_id)
        if role:
            item.role = RoleSummary.model_validate(role)
        out.append(item)
    return out


@router.post("/programmes", response_model=ProgrammeDetail, status_code=201)
def create_programme(
    payload: ProgrammeCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> ProgrammeDetail:
    """Admin creates the programme shell; the rubric is composed immediately
    from the role template so slots 2 and 3 arrive pre-filled (FR-055)."""
    if db.get(Company, payload.company_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found.")
    if db.get(Role, payload.role_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found.")
    clash = db.scalar(
        select(Programme)
        .where(Programme.company_id == payload.company_id)
        .where(Programme.slug == payload.slug)
    )
    if clash is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That slug is taken for this company.")

    programme = Programme(
        company_id=payload.company_id,
        role_id=payload.role_id,
        title=payload.title,
        slug=payload.slug,
        delivery_mode=DeliveryMode(payload.delivery_mode),
        capacity=payload.capacity,
        team_size_max=payload.team_size_max,
        applications_open_at=payload.applications_open_at,
        applications_close_at=payload.applications_close_at,
        start_at=payload.start_at,
        submit_deadline_at=payload.submit_deadline_at,
        winners_count=payload.winners_count,
        status=ProgrammeStatus.DRAFT,
    )
    db.add(programme)
    db.flush()

    try:
        compose_rubric(db, programme)
    except RubricError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    _seed_data_pack_from_role(db, programme)
    db.commit()
    return _detail(db, programme)


def _seed_data_pack_from_role(db: Session, programme: Programme) -> None:
    """FR-055/FR-057 — the role's validated public sources become the starting
    data pack. Unverified entries stay unverified; provenance is visible."""
    registry = db.scalars(
        select(DataPackResource).where(DataPackResource.role_id == programme.role_id)
    )
    for source in registry:
        db.add(
            DataPackResource(
                programme_id=programme.id,
                label=source.label,
                url_or_storage_key=source.url_or_storage_key,
                provenance=Provenance.PUBLIC,
                licence=source.licence,
                verification_status=source.verification_status,
                last_verified_at=source.last_verified_at,
            )
        )


@router.get("/programmes/{programme_id}", response_model=ProgrammeDetail)
def get_programme(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
) -> ProgrammeDetail:
    return _detail(db, programme)


@router.patch("/programmes/{programme_id}", response_model=ProgrammeDetail)
def update_programme(
    payload: ProgrammeUpdate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> ProgrammeDetail:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(programme, field, value)
    db.commit()
    return _detail(db, programme)


@router.patch("/programmes/{programme_id}/criteria/{criterion_id}", response_model=CriterionOut)
def update_criterion(
    criterion_id: uuid.UUID,
    payload: CriterionUpdate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> CriterionOut:
    """FR-072/074/076 — anchors are editable, universal names are not, and
    nothing is editable once judging has started."""
    criterion = db.get(RubricCriterion, criterion_id)
    if criterion is None or criterion.programme_id != programme.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Criterion not found.")
    try:
        edit_criterion(db, criterion, **payload.model_dump(exclude_unset=True))
    except RubricError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return CriterionOut(
        id=criterion.id,
        slot=criterion.slot,
        name=criterion.name,
        anchor_5=criterion.anchor_5,
        anchor_3=criterion.anchor_3,
        anchor_1=criterion.anchor_1,
        is_universal=criterion.is_universal,
    )


class PublicationCheck(BaseModel):
    ready: bool
    problems: list[str]


@router.get("/programmes/{programme_id}/publication-check", response_model=PublicationCheck)
def publication_check(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
) -> PublicationCheck:
    problems = validate_for_publication(db, programme)
    if programme.applications_close_at is None:
        problems.append("applications_close_at is not set")
    if programme.submit_deadline_at is None:
        problems.append("submit_deadline_at is not set")
    return PublicationCheck(ready=not problems, problems=problems)


@router.post("/programmes/{programme_id}/publish", response_model=ProgrammeDetail)
def publish_programme(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> ProgrammeDetail:
    """FR-075 — validation blocks publication with an incomplete rubric.
    Admin-gated: a company can draft, but only admin publishes (FR-019)."""
    try:
        publish(db, programme)
    except RubricError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _detail(db, programme)


@router.post("/programmes/{programme_id}/judging-sessions", status_code=201)
def add_judging_session(
    payload: JudgingSessionCreate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> dict:
    """Session times are fixed at setup and published in the brief, because
    participants are assigned to one at acceptance (FR-811b)."""
    row = JudgingSession(
        programme_id=programme.id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        location_or_meet_link=payload.location_or_meet_link,
        capacity=payload.capacity,
    )
    db.add(row)
    db.commit()
    return {"id": str(row.id), "starts_at": row.starts_at.isoformat()}


@router.get("/programmes/{programme_id}/data-pack")
def get_data_pack(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
) -> list[dict]:
    """FR-057/069 — one list, provenance visible per resource."""
    resources = db.scalars(
        select(DataPackResource).where(DataPackResource.programme_id == programme.id)
    )
    return [
        {
            "id": str(r.id),
            "label": r.label,
            "url": r.url_or_storage_key,
            "provenance": r.provenance.value,
            "licence": r.licence,
            "verification_status": r.verification_status.value,
            "last_verified_at": r.last_verified_at.isoformat() if r.last_verified_at else None,
        }
        for r in resources
    ]


@router.post("/programmes/{programme_id}/data-pack", status_code=201)
def add_data_pack_resource(
    payload: DataPackResourceCreate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> dict:
    """FR-066 — the public-data pack is the default, not the constraint.
    A company that will share real data produces a better challenge."""
    resource = DataPackResource(
        programme_id=programme.id,
        label=payload.label,
        url_or_storage_key=payload.url_or_storage_key,
        provenance=Provenance(payload.provenance),
        licence=payload.licence,
        verification_status=VerificationStatus.UNVERIFIED,
        uploaded_by=actor.id if actor.is_company_user else None,
    )
    db.add(resource)
    db.commit()
    return {"id": str(resource.id), "label": resource.label}


class DraftRequest(BaseModel):
    company_url: str | None = None
    admin_notes: str | None = Field(
        default=None,
        description="Anything from the intake conversation worth grounding the draft in",
    )


class DraftOut(BaseModel):
    id: uuid.UUID
    title: str
    context: str
    question: str
    outputs: list[str]
    grounding: str | None
    based_on_live_listing: bool
    model: str | None
    rendered: str
    accepted_at: datetime | None = None


def _draft_out(draft: ProblemStatementDraft, role_name: str) -> DraftOut:
    from projet.integrations.claude import ProblemStatementDraft as DraftDTO

    rendered = DraftDTO(
        title=draft.title,
        context=draft.context,
        question=draft.question,
        outputs=draft.outputs or [],
        grounding=draft.grounding or "",
        based_on_live_listing=draft.based_on_live_listing,
    ).render(1, role_name)
    return DraftOut(
        id=draft.id,
        title=draft.title,
        context=draft.context,
        question=draft.question,
        outputs=draft.outputs or [],
        grounding=draft.grounding,
        based_on_live_listing=draft.based_on_live_listing,
        model=draft.model,
        rendered=rendered,
        accepted_at=draft.accepted_at,
    )


@router.post("/programmes/{programme_id}/problem-statement/draft", response_model=DraftOut)
def draft_problem_statement_endpoint(
    payload: DraftRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> DraftOut:
    """FR-061 — draft from the role plus research on the company.

    Admin-only and never auto-published: the draft lands in a review queue
    (FR-063), and admin rewrites before anything reaches the company.
    """
    from projet.integrations.claude import DraftingUnavailable, draft_problem_statement
    from projet.models import RoleTemplate

    company = db.get(Company, programme.company_id)
    role = db.get(Role, programme.role_id)
    template = db.get(RoleTemplate, programme.role_id)
    if company is None or role is None or template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme is not fully configured.")

    try:
        drafted = draft_problem_statement(
            company_name=company.name,
            company_url=payload.company_url,
            role_name=role.name,
            deliverable=programme.deliverable_spec or template.default_deliverable,
            admin_notes=payload.admin_notes,
        )
    except DraftingUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error

    row = ProblemStatementDraft(
        programme_id=programme.id,
        title=drafted.title,
        context=drafted.context,
        question=drafted.question,
        outputs=drafted.outputs,
        grounding=drafted.grounding,
        based_on_live_listing=drafted.based_on_live_listing,
        model=drafted.model,
        created_by=actor.id,
    )
    db.add(row)
    db.commit()
    return _draft_out(row, role.name)


@router.get("/programmes/{programme_id}/problem-statement/drafts", response_model=list[DraftOut])
def list_drafts(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> list[DraftOut]:
    role = db.get(Role, programme.role_id)
    drafts = db.scalars(
        select(ProblemStatementDraft)
        .where(ProblemStatementDraft.programme_id == programme.id)
        .order_by(ProblemStatementDraft.created_at.desc())
    )
    return [_draft_out(d, role.name if role else "") for d in drafts]


class ProblemStatementUpdate(BaseModel):
    problem_statement: str
    deliverable_spec: str | None = None
    from_draft_id: uuid.UUID | None = None


@router.put("/programmes/{programme_id}/problem-statement", response_model=ProgrammeDetail)
def set_problem_statement(
    payload: ProblemStatementUpdate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> ProgrammeDetail:
    """FR-063/FR-067 — admin reviews and rewrites, and a company that knows
    exactly what it wants can say so and have that be what runs."""
    programme.problem_statement = payload.problem_statement
    if payload.deliverable_spec is not None:
        programme.deliverable_spec = payload.deliverable_spec
    if payload.from_draft_id is not None:
        draft = db.get(ProblemStatementDraft, payload.from_draft_id)
        if draft is not None and draft.programme_id == programme.id:
            draft.accepted_at = utcnow()
    db.commit()
    return _detail(db, programme)
