"""Programme setup, rubric authoring and the data pack (FR-050, FR-060, FR-070)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import (
    get_programme_or_404,
    require_company_manager,
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
from projet.services.data_pack import (
    ALLOWED_UPLOAD_TYPES,
    MAX_UPLOAD_BYTES,
    is_storage_key,
    new_storage_key,
    resource_url,
    sync_confidentiality_ack,
)
from projet.services.rubric import (
    RubricError,
    compose_rubric,
    edit_criterion,
    publish,
    validate_for_publication,
)
from projet.services.schedule import (
    ScheduleError,
    bind_dates,
)
from projet.storage import get_storage

router = APIRouter(tags=["programmes"])
log = logging.getLogger(__name__)


class ProgrammeCreate(BaseModel):
    company_id: uuid.UUID | None = None
    role_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(min_length=1, max_length=160)
    delivery_mode: str = DeliveryMode.ONLINE.value
    capacity: int | None = None
    applications_open_at: datetime | None = None
    applications_close_at: datetime | None = None
    start_at: datetime | None = Field(
        default=None,
        description="First day. Stored as 00:00 in the programme timezone.",
    )
    submit_deadline_at: datetime | None = Field(
        default=None,
        description="Last day. Stored as 23:59 in the programme timezone.",
    )
    # Usually filled in later, from a draft the company accepts and edits. They
    # are accepted here so a caller who already knows the brief is not forced
    # through a second request to say so.
    problem_statement: str | None = None
    deliverable_spec: str | None = None
    winners_count: int = 1


class ProgrammeUpdate(BaseModel):
    """The company picks the days; times of day are pinned on the server."""

    title: str | None = None
    brief_url: str | None = None
    problem_statement: str | None = None
    deliverable_spec: str | None = None
    capacity: int | None = None
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
    confidential: bool = Field(
        default=False,
        description="Behind an acknowledgement, and never named in the public listing.",
    )


class DataPackResourceUpdate(BaseModel):
    """Every field optional: this is the include/exclude toggle as much as an edit."""

    label: str | None = Field(default=None, min_length=1, max_length=300)
    url_or_storage_key: str | None = None
    licence: str | None = None
    included: bool | None = None
    confidential: bool | None = None


def _resource_out(resource: DataPackResource) -> dict:
    """One shape for the company-facing list, whether linked or uploaded."""
    return {
        "id": str(resource.id),
        "label": resource.label,
        "url": resource_url(resource.url_or_storage_key),
        "provenance": resource.provenance.value,
        "licence": resource.licence,
        "included": resource.included,
        "confidential": resource.confidential,
        "uploaded": resource.provenance is not Provenance.PUBLIC,
        "verification_status": resource.verification_status.value,
        "last_verified_at": (
            resource.last_verified_at.isoformat() if resource.last_verified_at else None
        ),
    }


def _resource_or_404(
    db: Session, programme: Programme, resource_id: uuid.UUID
) -> DataPackResource:
    resource = db.get(DataPackResource, resource_id)
    if resource is None or resource.programme_id != programme.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such resource in this data pack.")
    return resource


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
    actor: Actor = Depends(require_company_manager),
) -> ProgrammeDetail:
    """Company owners/admins create the programme shell for their own company;
    platform staff can create for any company. The rubric is composed
    immediately from the role template so slots 2 and 3 arrive pre-filled
    (FR-055)."""
    if actor.is_company_user:
        company_id = actor.company_id
    elif payload.company_id is not None:
        company_id = payload.company_id
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "company_id is required for platform users."
        )
    if db.get(Company, company_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found.")
    if db.get(Role, payload.role_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found.")
    clash = db.scalar(
        select(Programme)
        .where(Programme.company_id == company_id)
        .where(Programme.slug == payload.slug)
    )
    if clash is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That slug is taken for this company.")

    try:
        start_at, end_at, close_at = bind_dates(
            payload.start_at, payload.submit_deadline_at, payload.applications_close_at
        )
    except ScheduleError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    programme = Programme(
        company_id=company_id,
        role_id=payload.role_id,
        title=payload.title,
        slug=payload.slug,
        delivery_mode=DeliveryMode(payload.delivery_mode),
        capacity=payload.capacity,
        # Individuals only: one submission, one pitch, one verdict per person.
        team_size_max=1,
        applications_open_at=payload.applications_open_at,
        applications_close_at=close_at,
        start_at=start_at,
        submit_deadline_at=end_at,
        problem_statement=payload.problem_statement,
        deliverable_spec=payload.deliverable_spec,
        winners_count=payload.winners_count,
        status=ProgrammeStatus.DRAFT,
    )
    db.add(programme)
    db.flush()

    try:
        compose_rubric(db, programme)
    except RubricError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    db.commit()
    return _detail(db, programme)


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
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(programme, field, value)

    if {"start_at", "submit_deadline_at", "applications_close_at"} & changes.keys():
        try:
            start_at, end_at, close_at = bind_dates(
                programme.start_at,
                programme.submit_deadline_at,
                programme.applications_close_at,
            )
        except ScheduleError as error:
            db.rollback()
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
        programme.start_at = start_at
        programme.submit_deadline_at = end_at
        if programme.applications_close_at is not None:
            programme.applications_close_at = close_at

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
    # Blocking and advisory items are merged for display — the draft page
    # shows one list either way — but `ready` is judged on the blocking ones
    # only, via _setup_problems below.
    problems: list[str]


@router.get("/programmes/{programme_id}/publication-check", response_model=PublicationCheck)
def publication_check(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
) -> PublicationCheck:
    blocking = validate_for_publication(db, programme) + _setup_problems(programme)
    return PublicationCheck(
        ready=not blocking,
        problems=blocking + _setup_warnings(programme),
    )


def _setup_problems(programme: Programme) -> list[str]:
    """What blocks this from going live.

    Start and end dates are the hard block: the apply form's commitment
    checkbox has no days to name without them. The problem statement,
    deliverable and applications-close date are left to the company's
    judgement instead of enforced here — a company can publish a bare-bones
    shell to test the pipeline end to end and fill in the brief before a real
    applicant sees it. `publication-check` still surfaces the gaps below as
    warnings, not refusals, so the draft page keeps nudging without blocking.
    """
    problems: list[str] = []
    if programme.start_at is None:
        problems.append("No start date has been picked.")
    if programme.submit_deadline_at is None:
        problems.append("No end date has been picked.")
    return problems


def _setup_warnings(programme: Programme) -> list[str]:
    """Non-blocking nudges shown on the draft page, not enforced at publish."""
    warnings: list[str] = []
    if not (programme.problem_statement or "").strip():
        warnings.append("The problem statement is empty. Draft one or write your own.")
    if not (programme.deliverable_spec or "").strip():
        warnings.append(
            "The deliverable is not described, so applicants cannot know what to produce."
        )
    if programme.applications_close_at is None:
        warnings.append("Applications have no closing date.")
    return warnings


@router.post("/programmes/{programme_id}/publish", response_model=ProgrammeDetail)
def publish_programme(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> ProgrammeDetail:
    """FR-075 — validation blocks publication with an incomplete rubric, and
    the start and end dates run again here, because the company is not the
    only caller. The brief and applications-close date are the company's
    judgement call, not a gate — see _setup_problems.
    """
    setup = _setup_problems(programme)
    if setup:
        raise HTTPException(status.HTTP_409_CONFLICT, " ".join(setup))
    try:
        publish(db, programme)
    except RubricError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    from projet.services.calendar import ensure_kickoff_event

    # Publication is not held hostage to Calendar being up: the listing goes
    # live either way, and a programme without an event yet picks one up on the
    # next publish. Logged rather than swallowed, because the Meet link is what
    # the offer email carries.
    try:
        ensure_kickoff_event(db, programme)
    except Exception:
        log.exception("kickoff event not created for programme %s", programme.id)

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
    """FR-057/069 — one list, provenance visible per resource.

    The company sees what it excluded as well as what it kept, because an
    invisible exclusion is indistinguishable from a source that was never there.
    """
    resources = db.scalars(
        select(DataPackResource)
        .where(DataPackResource.programme_id == programme.id)
        .where(DataPackResource.provenance != Provenance.PUBLIC)
        .order_by(DataPackResource.created_at)
    )
    return [_resource_out(r) for r in resources]


@router.post("/programmes/{programme_id}/data-pack", status_code=201)
def add_data_pack_resource(
    payload: DataPackResourceCreate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> dict:
    """Add a link the company wants participants to work from."""
    resource = DataPackResource(
        programme_id=programme.id,
        label=payload.label,
        url_or_storage_key=payload.url_or_storage_key,
        provenance=Provenance(payload.provenance),
        licence=payload.licence,
        confidential=payload.confidential,
        verification_status=VerificationStatus.UNVERIFIED,
        uploaded_by=actor.id if actor.is_company_user else None,
    )
    db.add(resource)
    db.flush()
    sync_confidentiality_ack(db, programme)
    db.commit()
    return _resource_out(resource)


@router.post("/programmes/{programme_id}/data-pack/upload", status_code=201)
async def upload_data_pack_resource(
    file: UploadFile = File(),
    label: str | None = Form(default=None, max_length=300),
    licence: str | None = Form(default=None, max_length=200),
    confidential: bool = Form(default=False),
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> dict:
    """The company's own file, not a link to it.

    A shared Drive link is a permission the company has to keep right for a
    week; an upload is a copy we can serve, expire, and stop serving when the
    programme ends. Stored under a signed key, so a forwarded URL dies.
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "That file is over 100MB. Share it as a link instead.",
        )
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{file.content_type} is not an accepted file type.",
        )

    key = new_storage_key(programme.id, file.filename)
    get_storage().put(key, content, file.content_type)
    resource = DataPackResource(
        programme_id=programme.id,
        label=(label or "").strip() or (file.filename or "Uploaded resource"),
        url_or_storage_key=key,
        provenance=Provenance.COMPANY_SUPPLIED,
        licence=licence,
        confidential=confidential,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=utcnow(),
        uploaded_by=actor.id if actor.is_company_user else None,
    )
    db.add(resource)
    db.flush()
    sync_confidentiality_ack(db, programme)
    db.commit()
    return _resource_out(resource)


@router.patch("/programmes/{programme_id}/data-pack/{resource_id}")
def update_data_pack_resource(
    resource_id: uuid.UUID,
    payload: DataPackResourceUpdate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> dict:
    """Include, exclude, rename, or reclassify one entry."""
    resource = _resource_or_404(db, programme, resource_id)
    fields = payload.model_dump(exclude_unset=True)
    if "label" in fields and fields["label"]:
        resource.label = fields["label"].strip()
    if "url_or_storage_key" in fields:
        # Repointing an upload would orphan the stored object and hand out a
        # link under a key we still sign, so links only.
        if is_storage_key(resource.url_or_storage_key):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Upload a new file instead of repointing this one.",
            )
        resource.url_or_storage_key = fields["url_or_storage_key"]
    if "licence" in fields:
        resource.licence = fields["licence"]
    if fields.get("included") is not None:
        resource.included = fields["included"]
    if fields.get("confidential") is not None:
        resource.confidential = fields["confidential"]
    sync_confidentiality_ack(db, programme)
    db.commit()
    return _resource_out(resource)


@router.delete("/programmes/{programme_id}/data-pack/{resource_id}", status_code=204)
def delete_data_pack_resource(
    resource_id: uuid.UUID,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> Response:
    """Remove a resource the company put on this programme."""
    resource = _resource_or_404(db, programme, resource_id)
    if is_storage_key(resource.url_or_storage_key):
        get_storage().delete(resource.url_or_storage_key)
    db.delete(resource)
    db.flush()
    sync_confidentiality_ack(db, programme)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class DraftRequest(BaseModel):
    company_url: str | None = None
    admin_notes: str | None = Field(
        default=None,
        description="Anything from the intake conversation worth grounding the draft in",
    )


class DraftOut(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID | None = None
    # Which of the run's angles this is. The company chooses between them, so
    # the number has to mean the same thing on every screen.
    angle: int = 1
    title: str
    context: str
    question: str
    outputs: list[str]
    grounding: str | None
    based_on_live_listing: bool
    model: str | None
    # The angle in the plain-text shape the format specifies, ready to paste
    # into the problem statement as is.
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
    ).render(draft.angle, role_name)
    return DraftOut(
        id=draft.id,
        batch_id=draft.batch_id,
        angle=draft.angle,
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


@router.post(
    "/programmes/{programme_id}/problem-statement/draft", response_model=list[DraftOut]
)
def draft_problem_statement_endpoint(
    payload: DraftRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> list[DraftOut]:
    """FR-061 — two or three angles on the role, from research on the company.

    The company runs this themselves, and admin can run it for them: both pass
    this guard, and the company account is the one thing everything hangs off.

    Nothing is auto-published (FR-063). The angles land in a review list, the
    company picks one, and whoever is editing rewrites it before it runs.
    """
    from projet.integrations.claude import DraftingUnavailable, draft_problem_statements
    from projet.models import RoleTemplate

    company = db.get(Company, programme.company_id)
    role = db.get(Role, programme.role_id)
    template = db.get(RoleTemplate, programme.role_id)
    if company is None or role is None or template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme is not fully configured.")

    try:
        angles = draft_problem_statements(
            company_name=company.name,
            company_url=payload.company_url or company.website_url,
            role_name=role.name,
            deliverable=programme.deliverable_spec or template.default_deliverable,
            admin_notes=payload.admin_notes,
        )
    except DraftingUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error

    batch_id = uuid.uuid4()
    # One run, one timestamp. Letting each row take its own would order the
    # angles newest-first inside a batch, which reverses the offered order.
    drafted_at = utcnow()
    rows = [
        ProblemStatementDraft(
            programme_id=programme.id,
            batch_id=batch_id,
            angle=index,
            title=drafted.title,
            context=drafted.context,
            question=drafted.question,
            outputs=drafted.outputs,
            grounding=drafted.grounding,
            based_on_live_listing=drafted.based_on_live_listing,
            model=drafted.model,
            created_by=actor.id,
            created_at=drafted_at,
        )
        for index, drafted in enumerate(angles, start=1)
    ]
    db.add_all(rows)
    db.commit()
    return [_draft_out(row, role.name) for row in rows]


@router.get("/programmes/{programme_id}/problem-statement/drafts", response_model=list[DraftOut])
def list_drafts(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> list[DraftOut]:
    """Every angle drafted so far, newest run first, angles in offered order."""
    role = db.get(Role, programme.role_id)
    drafts = db.scalars(
        select(ProblemStatementDraft)
        .where(ProblemStatementDraft.programme_id == programme.id)
        .order_by(
            ProblemStatementDraft.created_at.desc(),
            ProblemStatementDraft.angle.asc(),
        )
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
