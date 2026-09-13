"""The applicant pipeline (FR-300) and offer acceptance (FR-400).

Acceptance rate target from FR-306's acceptance criteria: 120 applications
scored and dispositioned in under three hours. That means the list is the work
surface — filterable, sortable, keyboard-navigable, auto-saving — not a
reporting view.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import get_programme_or_404, require_company_manager, require_platform
from projet.db import get_session
from projet.models import Application, Programme
from projet.models.enums import ApplicationStatus
from projet.services.auth import Actor
from projet.services.selection import (
    SelectionError,
    accept_offer,
    make_offer,
    promote_from_waitlist,
    reject,
    score_application,
    seat_count,
)
from projet.storage import sign_key

router = APIRouter(tags=["applications"])


class ApplicationOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    name: str
    contact_email: str
    organisation: str | None
    year_course: str | None
    job_title: str | None
    status: str
    score_relevance: int | None
    score_specificity: int | None
    score_capability: int | None
    score_followthrough: int | None
    score_total: int | None
    consent_share_company: bool
    created_at: datetime
    offer_expires_at: datetime | None = None

    @classmethod
    def of(cls, application: Application) -> ApplicationOut:
        person = application.person
        return cls(
            id=application.id,
            person_id=person.id,
            name=person.name,
            contact_email=person.contact_email,
            organisation=person.organisation,
            year_course=person.year_course,
            job_title=person.job_title,
            status=application.status.value,
            score_relevance=application.score_relevance,
            score_specificity=application.score_specificity,
            score_capability=application.score_capability,
            score_followthrough=application.score_followthrough,
            score_total=application.score_total,
            consent_share_company=application.consent_share_company,
            created_at=application.created_at,
            offer_expires_at=application.offer_expires_at,
        )


class ApplicationDetail(ApplicationOut):
    """FR-303 — writeup and CV side by side, without leaving the list."""

    writeup: str | None = None
    cv_url: str | None = None
    linkedin_url: str | None = None
    # The declaration, shown alongside the writeup: a named conflict during the
    # week is something to read before offering a seat, not after.
    availability_confirmed: bool = False
    availability_note: str | None = None
    google_email: str | None = None
    phone: str | None = None


class SeatsOut(BaseModel):
    capacity: int | None
    taken: int
    pending: int
    remaining: int | None
    uncapped: bool


@router.get("/programmes/{programme_id}/applications", response_model=list[ApplicationOut])
def list_applications(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str = Query(default="score"),
) -> list[ApplicationOut]:
    """FR-301 — filterable by status, sortable by score."""
    statement = select(Application).where(Application.programme_id == programme.id)
    if status_filter:
        try:
            statement = statement.where(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown status {status_filter!r}."
            ) from None
    if sort == "score":
        statement = statement.order_by(
            Application.score_total.desc().nullslast(), Application.created_at
        )
    else:
        statement = statement.order_by(Application.created_at)
    return [ApplicationOut.of(a) for a in db.scalars(statement)]


@router.get("/programmes/{programme_id}/seats", response_model=SeatsOut)
def seats(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> SeatsOut:
    count = seat_count(db, programme)
    return SeatsOut(
        capacity=count.capacity,
        taken=count.taken,
        pending=count.pending,
        remaining=count.remaining,
        uncapped=count.uncapped,
    )


def _application_or_404(
    db: Session, programme: Programme, application_id: uuid.UUID
) -> Application:
    application = db.get(Application, application_id)
    if application is None or application.programme_id != programme.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")
    return application


@router.get(
    "/programmes/{programme_id}/applications/{application_id}",
    response_model=ApplicationDetail,
)
def get_application(
    application_id: uuid.UUID,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_company_manager),
) -> ApplicationDetail:
    application = _application_or_404(db, programme, application_id)
    base = ApplicationOut.of(application)
    detail = ApplicationDetail(**base.model_dump())
    detail.writeup = application.writeup
    detail.linkedin_url = application.linkedin_url
    detail.availability_confirmed = application.availability_confirmed
    detail.availability_note = application.availability_note
    detail.google_email = application.person.google_email
    detail.phone = application.person.phone
    if application.cv_url:
        # Section 8 — CVs are not publicly addressable; served through a signed,
        # expiring URL rather than a guessable path.
        detail.cv_url = f"/files/{application.cv_url}?sig={sign_key(application.cv_url)}"
    return detail


class ScoreRequest(BaseModel):
    relevance: int | None = Field(default=None, ge=1, le=5)
    specificity: int | None = Field(default=None, ge=1, le=5)
    capability: int | None = Field(default=None, ge=1, le=5)
    followthrough: int | None = Field(default=None, ge=1, le=5)


@router.patch(
    "/programmes/{programme_id}/applications/{application_id}/score",
    response_model=ApplicationOut,
)
def score(
    application_id: uuid.UUID,
    payload: ScoreRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> ApplicationOut:
    """FR-302 — auto-saving inline scoring. Admin-only: the prescreen rubric is
    never shown to companies or applicants (FR-079)."""
    application = _application_or_404(db, programme, application_id)
    try:
        score_application(db, application, **payload.model_dump(exclude_unset=True))
    except SelectionError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    db.commit()
    return ApplicationOut.of(application)


class DispositionRequest(BaseModel):
    application_ids: list[uuid.UUID] = Field(min_length=1)
    action: str = Field(pattern="^(offer|waitlist|reject)$")
    feedback: str | None = None


class DispositionResult(BaseModel):
    updated: int
    skipped: list[str] = []


@router.post(
    "/programmes/{programme_id}/applications/disposition", response_model=DispositionResult
)
def disposition(
    payload: DispositionRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_platform),
) -> DispositionResult:
    """FR-304 — bulk offer, waitlist and reject, each firing its email."""
    updated = 0
    skipped: list[str] = []
    for application_id in payload.application_ids:
        application = db.get(Application, application_id)
        if application is None or application.programme_id != programme.id:
            skipped.append(f"{application_id}: not found")
            continue
        try:
            if payload.action == "offer":
                make_offer(db, application)
            elif payload.action == "waitlist":
                waitlist_application(db, application)
            else:
                reject(db, application, payload.feedback)
            updated += 1
        except SelectionError as error:
            skipped.append(f"{application_id}: {error}")
    db.commit()
    return DispositionResult(updated=updated, skipped=skipped)


def waitlist_application(db: Session, application: Application) -> Application:
    from projet.services.selection import waitlist as _waitlist

    return _waitlist(db, application)


class AcceptRequest(BaseModel):
    token: str


class AcceptResponse(BaseModel):
    participant_id: uuid.UUID
    programme_title: str
    message: str


@router.post("/accept", response_model=AcceptResponse, tags=["public"])
def accept(payload: AcceptRequest, db: Session = Depends(get_session)) -> AcceptResponse:
    """FR-401 — tokenised, no login. One click from an email."""
    try:
        participant = accept_offer(db, payload.token)
    except SelectionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    programme = db.get(Programme, participant.programme_id)
    db.commit()
    return AcceptResponse(
        participant_id=participant.id,
        programme_title=programme.title if programme else "",
        message="You're confirmed. Check your email for the calendar invites.",
    )


class DeclineRequest(BaseModel):
    token: str


@router.post("/decline", tags=["public"])
def decline(payload: DeclineRequest, db: Session = Depends(get_session)) -> dict:
    """FR-403 — declining releases the seat and fires waitlist promotion
    immediately."""
    application = db.scalar(select(Application).where(Application.offer_token == payload.token))
    if application is None or application.status != ApplicationStatus.OFFERED:
        raise HTTPException(status.HTTP_409_CONFLICT, "That link is no longer valid.")

    application.status = ApplicationStatus.DECLINED
    application.offer_token = None
    db.flush()

    programme = db.get(Programme, application.programme_id)
    promoted = promote_from_waitlist(db, programme) if programme else []
    db.commit()
    return {"declined": True, "promoted": len(promoted)}
