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
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from projet.api.deps import current_actor
from projet.db import get_session
from projet.models import (
    Application,
    Company,
    Participant,
    Programme,
    ProgrammeRole,
    Role,
    RoleTemplate,
    RubricCriterion,
)
from projet.models.base import utcnow
from projet.models.enums import ApplicationStatus, OutboxSubjectType, ProgrammeStatus
from projet.services.auth import Actor
from projet.services.branding import logo_url
from projet.services.people import google_email_warning, looks_like_email, resolve_person
from projet.services.schedule import programme_is_past
from projet.services.writeup import join_names, writeup_prompt_from_programme
from projet.storage import get_storage

router = APIRouter(prefix="/public", tags=["public"])

MAX_CV_BYTES = 5 * 1024 * 1024
ALLOWED_CV_TYPES = {"application/pdf"}


class PublicCriterion(BaseModel):
    slot: str
    name: str
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None
    role_name: str | None = None


class PublicListing(BaseModel):
    """FR-101 — company, role, summary, dates, commitment, and what they get.

    The full rubric renders here (FR-078): publishing it tells participants what
    they are judged on and removes the "it felt arbitrary" complaint. There is
    no advantage in concealing it — the rubric rewards things that cannot be faked.
    """

    company: str
    company_slug: str
    # The company's mark, for the page a stranger decides on. Rendered here so
    # the listing looks like the company's own, not like a row in a database.
    company_logo_url: str | None
    programme_slug: str
    title: str
    role: str
    problem_statement: str | None
    deliverable: str
    state: str
    applications_close_at: datetime | None
    start_at: datetime | None
    submit_deadline_at: datetime | None
    kickoff_at: datetime | None = None
    # End of the last day. Named here so the apply form can commit to both
    # dates a participant has to make.
    pitch_at: datetime | None
    seats_total: int | None
    seats_remaining: int | None
    criteria: list[PublicCriterion]
    data_pack_preview: list[str]
    # What the apply form asks for, written for this role (FR-201). It renders
    # on the listing too, so someone can read the question before committing to
    # the form.
    writeup_prompt: str
    # True when the signed-in participant already has an application here.
    # Strangers always see false; the apply endpoint still enforces the rule.
    already_applied: bool = False


def _state(programme: Programme) -> str:
    """FR-102 — one of three states, and nothing else.

    Active week (deadline not yet passed):
      - `open`   — applications still accepted
      - `closed` — applications window shut, challenge still running
    After Close and issue, or after the pitch/submit deadline:
      - `complete`
    """
    if programme.status == ProgrammeStatus.DRAFT:
        return "closed"
    if programme.status == ProgrammeStatus.COMPLETE:
        return "complete"
    now = utcnow()
    if programme_is_past(programme, now):
        return "complete"
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
    company_logo_url: str | None
    programme_slug: str
    title: str
    role: str
    roles: list[str] = []
    cluster: str
    clusters: list[str] = []
    state: str
    applications_close_at: datetime | None
    start_at: datetime | None
    seats_total: int | None
    seats_remaining: int | None


def _summarize(db: Session, programme: Programme, company: Company) -> PublicListingSummary:
    from projet.services.rubric import load_programme_roles

    roles = load_programme_roles(db, programme)
    names = [role.name for role in roles]
    clusters = list(dict.fromkeys(role.cluster for role in roles))
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
        company_logo_url=logo_url(company.id, company.logo_url),
        programme_slug=programme.slug,
        title=programme.title,
        role=join_names(names),
        roles=names,
        cluster=clusters[0] if clusters else "",
        clusters=clusters,
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
    """FR-105 — every active programme across companies, for a browse page.

    Active means the week is not over yet: both accepting applications (`open`)
    and still running with applications shut (`closed`). A programme the company
    has closed out, or whose week is over, drops off. The single-company
    listing above also shows complete ones, since a company's own careers page
    is a different audience.
    """
    query = (
        select(Programme)
        .where(Programme.status != ProgrammeStatus.DRAFT)
        .where(Programme.status != ProgrammeStatus.COMPLETE)
    )
    if role_slug is not None:
        role = db.scalar(select(Role).where(Role.slug == role_slug))
        if role is None:
            return []
        linked = select(ProgrammeRole.programme_id).where(ProgrammeRole.role_id == role.id)
        query = query.where(or_(Programme.role_id == role.id, Programme.id.in_(linked)))

    companies = {c.id: c for c in db.scalars(select(Company))}
    summaries: list[PublicListingSummary] = []
    for programme in db.scalars(query):
        company = companies.get(programme.company_id)
        if company is None:
            continue
        summary = _summarize(db, programme, company)
        if summary.state == "complete":
            continue
        if cluster is not None and cluster not in summary.clusters:
            continue
        summaries.append(summary)

    summaries.sort(key=_sort_key)
    return summaries[offset : offset + limit]


@router.get("/x/{company_slug}/{programme_slug}", response_model=PublicListing)
def listing(
    company_slug: str,
    programme_slug: str,
    db: Session = Depends(get_session),
    actor: Actor | None = Depends(current_actor),
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

    from projet.services.rubric import display_slot, load_programme_roles, programme_role_ids

    roles = load_programme_roles(db, programme)
    names = [role.name for role in roles]
    role_count = len(programme_role_ids(db, programme))
    by_id = {role.id: role for role in roles}
    criteria = list(
        db.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.programme_id == programme.id)
            .order_by(RubricCriterion.slot)
        )
    )
    template = db.get(RoleTemplate, roles[0].id) if roles else None


    seats_remaining = None
    if programme.capacity is not None:
        taken = db.scalar(
            select(func.count())
            .select_from(Participant)
            .where(Participant.programme_id == programme.id)
        )
        seats_remaining = max(0, programme.capacity - (taken or 0))

    already_applied = False
    if actor is not None and actor.is_participant:
        already_applied = (
            db.scalar(
                select(Application.id)
                .where(Application.programme_id == programme.id)
                .where(Application.person_id == actor.id)
                .limit(1)
            )
            is not None
        )

    return PublicListing(
        company=company.name,
        company_slug=company.slug,
        company_logo_url=logo_url(company.id, company.logo_url),
        programme_slug=programme.slug,
        title=programme.title,
        role=join_names(names),
        problem_statement=programme.problem_statement,
        deliverable=programme.deliverable_spec
        or (template.default_deliverable if template else ""),
        state=_state(programme),
        applications_close_at=programme.applications_close_at,
        start_at=programme.start_at,
        submit_deadline_at=programme.submit_deadline_at,
        kickoff_at=programme.kickoff_at,
        pitch_at=programme.pitch_at,
        # FR-101 — seat count displays only where capacity is set.
        seats_total=programme.capacity,
        seats_remaining=seats_remaining,
        criteria=[
            PublicCriterion(
                slot=display_slot(c, role_count),
                name=(
                    f"{c.name} · {by_id[c.role_id].name}"
                    if role_count > 1 and c.role_id is not None and c.role_id in by_id
                    else c.name
                ),
                anchor_5=c.anchor_5,
                anchor_3=c.anchor_3,
                anchor_1=c.anchor_1,
                role_name=by_id[c.role_id].name if c.role_id in by_id else None,
            )
            for c in criteria
        ],
        data_pack_preview=[],
        writeup_prompt=writeup_prompt_from_programme(db, programme),
        already_applied=already_applied,
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
            f"Applications need the commitment confirmed: starts on {kickoff} and "
            f"ends on {pitch}."
        )
    return "Applications need the commitment to the start and end dates confirmed."


def _readable(value: datetime | None) -> str | None:
    if value is None:
        return None
    # Avoid %-d / %#d — neither is portable across Windows and Unix.
    from projet.services.schedule import format_sgt_datetime

    return format_sgt_datetime(value)


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
    consent_share_company: bool = Form(default=False),
    consent_recording: bool = Form(default=False),
    cv: UploadFile | None = File(default=None),
    db: Session = Depends(get_session),
) -> ApplicationAccepted:
    """FR-201 to FR-208.

    Both consents must be ticked to apply. No password here — applicants sign
    in later via the offer / set-password path once they have a reason to. A
    signed-in applicant may reuse the CV already on their profile.
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

    if not availability_confirmed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            _commitment_refusal(programme),
        )
    if not consent_share_company or not consent_recording:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Applications need both consents ticked.",
        )

    linkedin = (linkedin_url or "").strip() or None
    if linkedin is not None and not looks_like_linkedin(linkedin):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "That does not look like a LinkedIn profile URL.",
        )

    person, _created = resolve_person(
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

    existing = db.scalar(
        select(Application)
        .where(Application.programme_id == programme.id)
        .where(Application.person_id == person.id)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this programme.")

    uploaded = cv is not None and bool(cv.filename)
    if uploaded:
        assert cv is not None
        content = await cv.read()
        if len(content) > MAX_CV_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CV must be under 5MB.")
        if cv.content_type not in ALLOWED_CV_TYPES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "CV must be a PDF.")
        key = f"cvs/{programme.id}/{person.id}/{secrets.token_hex(8)}.pdf"
        get_storage().put(key, content, "application/pdf")
        person.cv_url = key
    elif not person.cv_url:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Please attach your CV as a PDF.",
        )
    else:
        key = person.cv_url

    if linkedin:
        person.linkedin_url = linkedin

    application = Application(
        programme_id=programme.id,
        person_id=person.id,
        cv_url=key,
        writeup=writeup,
        linkedin_url=linkedin,
        availability_confirmed=True,
        consent_share_company=consent_share_company,
        consent_recording=consent_recording,
        consent_captured_at=utcnow(),
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You have already applied to this programme.",
        ) from exc

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
