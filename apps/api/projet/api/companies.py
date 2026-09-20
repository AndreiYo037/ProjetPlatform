"""Company accounts, team management and company home (FR-010, FR-017).

FR-016: adding a second judge is the owner inviting a colleague, not an admin
request to Andrei. That is the whole point of companies having real accounts.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.access import company_candidate_pool
from projet.api.deps import (
    require_actor,
    require_company_manager,
    require_platform,
    visible_programmes,
)
from projet.api.schemas import (
    CompanySummary,
    CompanyUserInvite,
    CompanyUserOut,
    ProgrammeOut,
    RoleSummary,
)
from projet.db import get_session
from projet.models import Company, CompanyUser, Programme, ProgrammeAssignment, Role
from projet.models.base import utcnow
from projet.models.enums import (
    CompanyUserRole,
    CompanyUserStatus,
    OutboxSubjectType,
    ProgrammeStatus,
)
from projet.models.people import normalise_email
from projet.outbox.account_effects import SET_PASSWORD_EMAIL
from projet.outbox.effects import enqueue
from projet.services.auth import (
    Actor,
    account_action_url,
    issue_account_action_token,
)
from projet.services.branding import (
    LOGO_TYPES,
    MAX_LOGO_BYTES,
    is_stored_logo,
    logo_media_type,
    new_logo_key,
)
from projet.services.people import looks_like_email
from projet.services.rubric import programme_role_ids
from projet.services.schedule import programme_is_past
from projet.storage import StorageError, get_storage

router = APIRouter(tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    slug: str
    owner_name: str
    owner_email: str
    contact_name: str | None = None
    tier: str = "sme"


class CandidateOut(BaseModel):
    id: uuid.UUID
    name: str
    organisation: str | None = None
    job_title: str | None = None
    year_course: str | None = None


class CompanyHome(BaseModel):
    """FR-017 — what a company user sees on signing in."""

    company: CompanySummary
    active_programmes: list[ProgrammeOut]
    draft_programmes: list[ProgrammeOut]
    past_programmes: list[ProgrammeOut]
    team: list[CompanyUserOut]
    candidate_pool_size: int


class CompanyProfileUpdate(BaseModel):
    name: str | None = None
    your_name: str | None = None
    # Read when drafting a problem statement, so it is worth asking for: a
    # research pass with the real site behind it beats one guessing from a name.
    website_url: str | None = None


def _company_or_404(db: Session, company_id: uuid.UUID, actor: Actor) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found.")
    if not actor.is_platform and actor.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found.")
    return company


@router.post("/companies", response_model=CompanySummary, status_code=201)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> Company:
    """FR-014 — admin creates the company and its first user, the owner.
    The owner invites everyone else themselves."""
    if db.scalar(select(Company).where(Company.slug == payload.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "That slug is already taken.")
    if not looks_like_email(payload.owner_email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid owner email.")

    company = Company(
        name=payload.name,
        slug=payload.slug,
        contact_name=payload.contact_name or payload.owner_name,
        contact_email=normalise_email(payload.owner_email),
        tier=payload.tier,
    )
    db.add(company)
    db.flush()
    owner = CompanyUser(
        company_id=company.id,
        name=payload.owner_name,
        email=normalise_email(payload.owner_email) or payload.owner_email,
        role=CompanyUserRole.OWNER,
        status=CompanyUserStatus.INVITED,
    )
    db.add(owner)
    db.flush()

    from projet.models.enums import AccountActionPurpose, ActorType

    token, raw = issue_account_action_token(
        db,
        actor_type=ActorType.COMPANY_USER,
        subject_id=owner.id,
        email=owner.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
        redirect_path="/company",
    )
    enqueue(
        db,
        subject_type=OutboxSubjectType.ACCOUNT_ACTION,
        subject_id=token.id,
        effect_type=SET_PASSWORD_EMAIL,
        payload={"url": account_action_url(token, raw)},
    )
    db.commit()
    return company


@router.patch("/companies/{company_id}", response_model=CompanySummary)
def update_company_profile(
    company_id: uuid.UUID,
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> Company:
    company = _company_or_404(db, company_id, actor)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Company name is required.")
        company.name = name
    if payload.your_name is not None and actor.is_company_user:
        user = db.get(CompanyUser, actor.id)
        if user is not None:
            label = payload.your_name.strip()
            if not label:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Your name is required.")
            user.name = label
            company.contact_name = label
    if payload.website_url is not None:
        company.website_url = payload.website_url.strip() or None
    db.commit()
    db.refresh(company)
    return company


@router.post("/companies/{company_id}/logo", response_model=CompanySummary, status_code=201)
async def upload_company_logo(
    company_id: uuid.UUID,
    file: UploadFile = File(),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> Company:
    """The mark that appears on the challenge the company publishes.

    Replacing one writes a new key and drops the old object, so a cached page
    never shows the previous logo under the same address.
    """
    content = await file.read()
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Logos must be under 2MB. A 512px square is plenty.",
        )
    if file.content_type not in LOGO_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Logos must be a PNG, JPEG or WebP image.",
        )

    company = _company_or_404(db, company_id, actor)
    previous = company.logo_url
    key = new_logo_key(company.id, file.content_type)
    get_storage().put(key, content, file.content_type)
    company.logo_url = key
    db.commit()
    if is_stored_logo(previous) and previous != key:
        get_storage().delete(previous)
    db.refresh(company)
    return company


@router.delete("/companies/{company_id}/logo", response_model=CompanySummary)
def remove_company_logo(
    company_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> Company:
    company = _company_or_404(db, company_id, actor)
    previous = company.logo_url
    company.logo_url = None
    db.commit()
    if is_stored_logo(previous):
        get_storage().delete(previous)
    db.refresh(company)
    return company


@router.get("/companies/{company_id}/logo", tags=["public"])
def serve_company_logo(
    company_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> Response:
    """Unsigned on purpose.

    The listing and the directory are read without a session, so the logo on
    them has to be too. Only raster images are ever stored here, and the media
    type comes from the extension we chose at upload rather than from anything
    the uploader sent.
    """
    company = db.get(Company, company_id)
    if company is None or not is_stored_logo(company.logo_url):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No logo.")
    try:
        content = get_storage().get(company.logo_url)
    except StorageError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No logo.") from None
    return Response(
        content,
        media_type=logo_media_type(company.logo_url),
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/companies/{company_id}/home", response_model=CompanyHome)
def company_home(
    company_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> CompanyHome:
    company = _company_or_404(db, company_id, actor)

    programmes = list(
        db.scalars(visible_programmes(db, actor).where(Programme.company_id == company.id))
    )
    role_ids = {rid for p in programmes for rid in programme_role_ids(db, p)}
    roles = (
        {role.id: role for role in db.scalars(select(Role).where(Role.id.in_(role_ids)))}
        if role_ids
        else {}
    )
    now = utcnow()
    drafts = [p for p in programmes if p.status == ProgrammeStatus.DRAFT]
    published = [p for p in programmes if p.status != ProgrammeStatus.DRAFT]
    active = [p for p in published if not programme_is_past(p, now)]
    past = [p for p in published if programme_is_past(p, now)]
    # Newest work first on Active and Drafts; most recently finished first on Past.
    drafts.sort(key=lambda p: p.created_at, reverse=True)
    active.sort(key=lambda p: p.created_at, reverse=True)
    past.sort(
        key=lambda p: p.pitch_at or p.submit_deadline_at or p.created_at,
        reverse=True,
    )

    team: list[CompanyUser] = []
    if actor.is_platform or actor.role in {
        CompanyUserRole.OWNER.value,
        CompanyUserRole.ADMIN.value,
    }:
        team = list(db.scalars(select(CompanyUser).where(CompanyUser.company_id == company.id)))

    # FR-018 — the pool is the retention mechanism, so its size is the headline.
    pool_size = len(list(db.scalars(company_candidate_pool(company.id))))

    return CompanyHome(
        company=CompanySummary.model_validate(company),
        active_programmes=[_programme_out(db, p, roles) for p in active],
        draft_programmes=[_programme_out(db, p, roles) for p in drafts],
        past_programmes=[_programme_out(db, p, roles) for p in past],
        team=[CompanyUserOut.model_validate(u) for u in team],
        candidate_pool_size=pool_size,
    )


def _programme_out(db: Session, programme: Programme, roles: dict) -> ProgrammeOut:
    data = ProgrammeOut.model_validate(programme)
    data.roles = [
        RoleSummary.model_validate(roles[rid])
        for rid in programme_role_ids(db, programme)
        if rid in roles
    ]
    data.role = data.roles[0] if data.roles else None
    return data


@router.get("/companies/{company_id}/candidates", response_model=list[CandidateOut])
def candidate_pool(
    company_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> list[CandidateOut]:
    """FR-018 — everyone who consented, across every programme this company has
    run. Consent is enforced by the query, not by this route (section 8)."""
    company = _company_or_404(db, company_id, actor)
    people = db.scalars(company_candidate_pool(company.id))
    return [
        CandidateOut(
            id=person.id,
            name=person.name,
            organisation=person.organisation,
            job_title=person.job_title,
            year_course=person.year_course,
        )
        for person in people
    ]


@router.get("/companies/{company_id}/users", response_model=list[CompanyUserOut])
def list_users(
    company_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> list[CompanyUser]:
    company = _company_or_404(db, company_id, actor)
    return list(db.scalars(select(CompanyUser).where(CompanyUser.company_id == company.id)))


@router.post("/companies/{company_id}/users", response_model=CompanyUserOut, status_code=201)
def invite_user(
    company_id: uuid.UUID,
    payload: CompanyUserInvite,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> CompanyUser:
    """FR-016 — the owner invites a colleague directly. No admin in the loop."""
    company = _company_or_404(db, company_id, actor)
    email = normalise_email(payload.email)
    if not looks_like_email(email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email address.")
    try:
        role = CompanyUserRole(payload.role)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown role {payload.role!r}."
        ) from None
    promoting_to_owner = role == CompanyUserRole.OWNER and not actor.is_platform
    if promoting_to_owner and actor.role != CompanyUserRole.OWNER.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an owner can add an owner.")

    existing = db.scalar(
        select(CompanyUser)
        .where(CompanyUser.company_id == company.id)
        .where(CompanyUser.email == email)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That person is already on the team.")

    user = CompanyUser(
        company_id=company.id,
        name=payload.name,
        email=email or payload.email,
        title=payload.title,
        role=role,
        status=CompanyUserStatus.INVITED,
        invited_by=actor.id if actor.is_company_user else None,
    )
    db.add(user)
    db.flush()

    # FR-016 — the invite is the account; they choose their own password to
    # activate it, same as any normal signup.
    from projet.models.enums import AccountActionPurpose, ActorType

    token, raw = issue_account_action_token(
        db,
        actor_type=ActorType.COMPANY_USER,
        subject_id=user.id,
        email=user.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
        redirect_path="/company",
    )
    enqueue(
        db,
        subject_type=OutboxSubjectType.ACCOUNT_ACTION,
        subject_id=token.id,
        effect_type=SET_PASSWORD_EMAIL,
        payload={"url": account_action_url(token, raw)},
    )
    db.commit()
    return user


@router.delete("/companies/{company_id}/users/{user_id}", status_code=204)
def disable_user(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> None:
    """Disabled rather than deleted: their scores and testimonials must keep
    their attribution."""
    company = _company_or_404(db, company_id, actor)
    user = db.get(CompanyUser, user_id)
    if user is None or user.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot disable your own account.")

    owners = list(
        db.scalars(
            select(CompanyUser)
            .where(CompanyUser.company_id == company.id)
            .where(CompanyUser.role == CompanyUserRole.OWNER)
            .where(CompanyUser.status != CompanyUserStatus.DISABLED)
        )
    )
    if user.role == CompanyUserRole.OWNER and len(owners) <= 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "That is the last owner; promote someone else first.",
        )

    user.status = CompanyUserStatus.DISABLED
    from projet.models.enums import ActorType
    from projet.services.auth import revoke_all_sessions

    revoke_all_sessions(db, ActorType.COMPANY_USER, user.id)
    db.commit()


class AssignmentRequest(BaseModel):
    company_user_id: uuid.UUID
    can_score: bool = True


@router.put("/programmes/{programme_id}/assignments", status_code=204)
def assign_rep(
    programme_id: uuid.UUID,
    payload: AssignmentRequest,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> None:
    """FR-015 — this is what scopes a rep to their own challenge."""
    programme = db.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme not found.")
    if not actor.is_platform and programme.company_id != actor.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme not found.")

    user = db.get(CompanyUser, payload.company_user_id)
    if user is None or user.company_id != programme.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in this company.")

    existing = db.get(ProgrammeAssignment, (programme.id, user.id))
    if existing is None:
        db.add(
            ProgrammeAssignment(
                programme_id=programme.id,
                company_user_id=user.id,
                can_score=payload.can_score,
            )
        )
    else:
        existing.can_score = payload.can_score
    db.commit()
