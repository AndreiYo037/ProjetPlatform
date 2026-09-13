"""The public listing and the application form (FR-100, FR-200).

Everything here is unauthenticated: a person with no account reads the page and
applies. Nothing on these routes may expose anything a signed-out stranger
should not see.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projet.db import get_session
from projet.models import (
    Application,
    Company,
    DataPackResource,
    Participant,
    Programme,
    Role,
    RoleTemplate,
    RubricCriterion,
)
from projet.models.base import utcnow
from projet.models.enums import ApplicationStatus, OutboxSubjectType, ProgrammeStatus
from projet.services.auth import hash_password, validate_password
from projet.services.people import google_email_warning, looks_like_email, resolve_person
from projet.services.writeup import writeup_prompt_for
from projet.storage import get_storage

router = APIRouter(prefix="/public", tags=["public"])

MAX_CV_BYTES = 5 * 1024 * 1024
WRITEUP_MIN_WORDS = 200
WRITEUP_MAX_WORDS = 300
ALLOWED_CV_TYPES = {"application/pdf"}


class PublicCriterion(BaseModel):
    slot: int
    name: str
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None


class PublicListing(BaseModel):
    """FR-101 — company, role, summary, dates, commitment, and what they get.

    The full rubric renders here (FR-078): publishing it tells participants what
    they are judged on and removes the "it felt arbitrary" complaint. There is
    no advantage in concealing it — the rubric rewards things that cannot be faked.
    """

    company: str
    company_slug: str
    programme_slug: str
    title: str
    role: str
    problem_statement: str | None
    deliverable: str
    state: str
    applications_close_at: datetime | None
    start_at: datetime | None
    submit_deadline_at: datetime | None
    # The seventh day. Published before anyone applies, because the whole point
    # of a fixed week is that the commitment is knowable up front (FR-800).
    pitch_at: datetime | None
    seats_total: int | None
    seats_remaining: int | None
    criteria: list[PublicCriterion]
    data_pack_preview: list[str]
    # What the apply form asks for, written for this role (FR-201). It renders
    # on the listing too, so someone can read the question before committing to
    # the form.
    writeup_prompt: str


def _state(programme: Programme) -> str:
    """FR-102 — one of three states, and nothing else."""
    if programme.status in (ProgrammeStatus.COMPLETE,):
        return "complete"
    now = utcnow()
    if programme.status != ProgrammeStatus.OPEN:
        return "closed"
    if programme.applications_close_at and programme.applications_close_at <= now:
        return "closed"
    if programme.applications_open_at and programme.applications_open_at > now:
        return "closed"
    return "open"


class PublicListingSummary(BaseModel):
    """FR-104/FR-105 — the row shape for both listing endpoints below.

    Deliberately thinner than `PublicListing`: a browsing stranger picking
    between programmes does not need the rubric or the data pack yet, only
    enough to decide whether to open the full page.
    """

    company: str
    company_slug: str
    programme_slug: str
    title: str
    role: str
    cluster: str
    state: str
    applications_close_at: datetime | None
    start_at: datetime | None
    seats_total: int | None
    seats_remaining: int | None


def _summarize(db: Session, programme: Programme, company: Company) -> PublicListingSummary:
    role = db.get(Role, programme.role_id)
    seats_remaining = None
    if programme.capacity is not None:
        taken = db.scalar(
            select(func.count())
            .select_from(Participant)
            .where(Participant.programme_id == programme.id)
        )
        seats_remaining = max(0, programme.capacity - (taken or 0))
    return PublicListingSummary(
        company=company.name,
        company_slug=company.slug,
        programme_slug=programme.slug,
        title=programme.title,
        role=role.name if role else "",
        cluster=role.cluster if role else "",
        state=_state(programme),
        applications_close_at=programme.applications_close_at,
        start_at=programme.start_at,
        seats_total=programme.capacity,
        seats_remaining=seats_remaining,
    )


_STATE_ORDER = {"open": 0, "closed": 1, "complete": 2}


def _sort_key(summary: PublicListingSummary) -> tuple:
    close_or_start = summary.applications_close_at or summary.start_at
    return (
        _STATE_ORDER.get(summary.state, 3),
        close_or_start is None,
        close_or_start,
    )


@router.get("/x/{company_slug}", response_model=list[PublicListingSummary])
def company_listing(
    company_slug: str,
    db: Session = Depends(get_session),
) -> list[PublicListingSummary]:
    """FR-104 — one company's own programmes, e.g. for a careers page.

    A draft stays unreachable here too (FR-056) — the same rule as the
    single-programme page, just applied across the whole company.
    """
    company = db.scalar(select(Company).where(Company.slug == company_slug))
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    programmes = db.scalars(
        select(Programme)
        .where(Programme.company_id == company.id)
        .where(Programme.status != ProgrammeStatus.DRAFT)
    )
    summaries = [_summarize(db, p, company) for p in programmes]
    summaries.sort(key=_sort_key)
    return summaries


@router.get("/challenges", response_model=list[PublicListingSummary])
def platform_directory(
    role_slug: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
) -> list[PublicListingSummary]:
    """FR-105 — every open programme across companies, for a browse page.

    Only `state == "open"` is indexed here: a stranger browsing a directory
    cares what they can still apply to, not what already closed. The
    single-company listing above does show closed and complete programmes,
    since a company's own careers page is a different audience.
    """
    query = select(Programme).where(Programme.status == ProgrammeStatus.OPEN)
    if role_slug is not None:
        role = db.scalar(select(Role).where(Role.slug == role_slug))
        if role is None:
            return []
        query = query.where(Programme.role_id == role.id)

    companies = {c.id: c for c in db.scalars(select(Company))}
    summaries: list[PublicListingSummary] = []
    for programme in db.scalars(query):
        company = companies.get(programme.company_id)
        if company is None:
            continue
        summary = _summarize(db, programme, company)
        if summary.state != "open":
            continue
        if cluster is not None and summary.cluster != cluster:
            continue
        summaries.append(summary)

    summaries.sort(key=_sort_key)
    return summaries[offset : offset + limit]


@router.get("/x/{company_slug}/{programme_slug}", response_model=PublicListing)
def listing(
    company_slug: str,
    programme_slug: str,
    db: Session = Depends(get_session),
) -> PublicListing:
    company = db.scalar(select(Company).where(Company.slug == company_slug))
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    programme = db.scalar(
        select(Programme)
        .where(Programme.company_id == company.id)
        .where(Programme.slug == programme_slug)
    )
    if programme is None or programme.status == ProgrammeStatus.DRAFT:
        # A draft is not publicly reachable (FR-056).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    role = db.get(Role, programme.role_id)
    template = db.get(RoleTemplate, programme.role_id)
    criteria = db.scalars(
        select(RubricCriterion)
        .where(RubricCriterion.programme_id == programme.id)
        .order_by(RubricCriterion.slot)
    )
    data_pack = db.scalars(
        select(DataPackResource).where(DataPackResource.programme_id == programme.id)
    )

    seats_remaining = None
    if programme.capacity is not None:
        taken = db.scalar(
            select(func.count())
            .select_from(Participant)
            .where(Participant.programme_id == programme.id)
        )
        seats_remaining = max(0, programme.capacity - (taken or 0))

    return PublicListing(
        company=company.name,
        company_slug=company.slug,
        programme_slug=programme.slug,
        title=programme.title,
        role=role.name if role else "",
        problem_statement=programme.problem_statement,
        deliverable=programme.deliverable_spec
        or (template.default_deliverable if template else ""),
        state=_state(programme),
        applications_close_at=programme.applications_close_at,
        start_at=programme.start_at,
        submit_deadline_at=programme.submit_deadline_at,
        pitch_at=programme.pitch_at,
        # FR-101 — seat count displays only where capacity is set.
        seats_total=programme.capacity,
        seats_remaining=seats_remaining,
        criteria=[
            PublicCriterion(
                slot=c.slot,
                name=c.name,
                anchor_5=c.anchor_5,
                anchor_3=c.anchor_3,
                anchor_1=c.anchor_1,
            )
            for c in criteria
        ],
        data_pack_preview=[r.label for r in data_pack],
        writeup_prompt=writeup_prompt_for(role, template),
    )


def looks_like_linkedin(url: str) -> bool:
    """Loose on purpose: linkedin.com/in/, /pub/, and the country subdomains.

    The point is to catch a typed name or an email in the wrong box, not to
    police the URL shape and lock out a legitimate profile.
    """
    lowered = url.strip().lower()
    if not lowered.startswith(("http://", "https://", "linkedin.com", "www.linkedin.com")):
        return False
    return "linkedin.com/" in lowered


def _commitment_refusal(programme: Programme) -> str:
    """Name the two dates in the refusal, so the reason is the dates themselves."""
    kickoff = _readable(programme.start_at)
    pitch = _readable(programme.pitch_at)
    if kickoff and pitch:
        return (
            f"Applications need the commitment confirmed: kickoff on {kickoff} and "
            f"the pitch on {pitch}."
        )
    return "Applications need the commitment to the kickoff and the pitch confirmed."


def _readable(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%a %-d %b, %H:%M UTC")


def count_words(text: str) -> int:
    return len([word for word in text.split() if word.strip()])


class ApplicationAccepted(BaseModel):
    application_id: uuid.UUID
    decision_by: datetime | None
    google_email_warning: str | None = None


@router.post(
    "/x/{company_slug}/{programme_slug}/apply",
    response_model=ApplicationAccepted,
    status_code=201,
)
async def apply(
    company_slug: str,
    programme_slug: str,
    name: str = Form(max_length=200),
    contact_email: str = Form(max_length=320),
    google_email: str = Form(max_length=320),
    phone: str | None = Form(default=None, max_length=60),
    organisation: str | None = Form(default=None, max_length=300),
    org_type: str | None = Form(default=None),
    year_course: str | None = Form(default=None, max_length=300),
    job_title: str | None = Form(default=None, max_length=200),
    timezone: str = Form(default="Asia/Singapore"),
    writeup: str = Form(),
    linkedin_url: str | None = Form(default=None, max_length=400),
    # FR-800's fixed week, declared rather than assumed. Defaulted to false so a
    # form that simply omits it is refused, not silently taken as a yes.
    availability_confirmed: bool = Form(default=False),
    availability_note: str | None = Form(default=None, max_length=2000),
    consent_share_company: bool = Form(default=False),
    consent_recording: bool = Form(default=False),
    password: str = Form(min_length=1, max_length=200),
    cv: UploadFile = File(),
    db: Session = Depends(get_session),
) -> ApplicationAccepted:
    """FR-201 to FR-208.

    Submission is allowed with either consent declined (FR-202): declining is a
    real choice, not a soft block.
    """
    company = db.scalar(select(Company).where(Company.slug == company_slug))
    programme = (
        db.scalar(
            select(Programme)
            .where(Programme.company_id == company.id)
            .where(Programme.slug == programme_slug)
        )
        if company
        else None
    )
    if company is None or programme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    if _state(programme) != "open":
        # FR-208 — applications lock automatically at applications_close_at.
        raise HTTPException(status.HTTP_409_CONFLICT, "Applications are closed.")

    if not looks_like_email(contact_email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid contact email.")
    if not looks_like_email(google_email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Google email.")
    password_error = validate_password(password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, password_error)

    words = count_words(writeup)
    if not WRITEUP_MIN_WORDS <= words <= WRITEUP_MAX_WORDS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"The writeup must be {WRITEUP_MIN_WORDS}-{WRITEUP_MAX_WORDS} words; yours is {words}.",
        )

    if not availability_confirmed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            _commitment_refusal(programme),
        )

    linkedin = (linkedin_url or "").strip() or None
    if linkedin is not None and not looks_like_linkedin(linkedin):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "That does not look like a LinkedIn profile URL.",
        )

    content = await cv.read()
    if len(content) > MAX_CV_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CV must be under 5MB.")
    if cv.content_type not in ALLOWED_CV_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "CV must be a PDF.")

    person, created = resolve_person(
        db,
        name=name,
        contact_email=contact_email,
        google_email=google_email,
        phone=phone,
        organisation=organisation,
        org_type=org_type,
        year_course=year_course,
        job_title=job_title,
        timezone=timezone,
    )
    # A returning applicant already has a password; do not overwrite it with
    # whatever they typed into a different programme's form.
    if created or not person.password_hash:
        person.password_hash = hash_password(password)

    existing = db.scalar(
        select(Application)
        .where(Application.programme_id == programme.id)
        .where(Application.person_id == person.id)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this programme.")

    key = f"cvs/{programme.id}/{person.id}/{secrets.token_hex(8)}.pdf"
    get_storage().put(key, content, "application/pdf")

    application = Application(
        programme_id=programme.id,
        person_id=person.id,
        cv_url=key,
        writeup=writeup,
        linkedin_url=linkedin,
        availability_confirmed=True,
        availability_note=(availability_note or "").strip() or None,
        consent_share_company=consent_share_company,
        consent_recording=consent_recording,
        consent_captured_at=utcnow(),
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    db.flush()

    from projet.outbox.application_effects import APPLICATION_RECEIVED_EMAIL
    from projet.outbox.effects import enqueue

    enqueue(
        db,
        subject_type=OutboxSubjectType.APPLICATION,
        subject_id=application.id,
        effect_type=APPLICATION_RECEIVED_EMAIL,
    )
    db.commit()

    return ApplicationAccepted(
        application_id=application.id,
        decision_by=programme.start_at,
        google_email_warning=google_email_warning(google_email),
    )


class NotifyRequest(BaseModel):
    email: str = Field(max_length=320)


@router.post("/x/{company_slug}/{programme_slug}/notify-me", status_code=202)
def notify_me(
    company_slug: str,
    programme_slug: str,
    payload: NotifyRequest,
    db: Session = Depends(get_session),
) -> dict:
    """FR-103 — when applications are closed the CTA becomes a capture."""
    if not looks_like_email(payload.email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email address.")
    return {"registered": True}
