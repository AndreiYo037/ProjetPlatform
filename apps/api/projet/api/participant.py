"""The participant's own view (FR-500, FR-700, FR-800).

Everything here is scoped to the signed-in participant. A participant-facing
schema has no field for a score, a ranking or a referral flag, so section 8's
rule holds by construction rather than by remembering to omit them (FR-1004).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import require_participant
from projet.db import get_session
from projet.models import (
    DataPackResource,
    JudgingSession,
    Participant,
    Post,
    Programme,
    Role,
    RoleTemplate,
    RubricCriterion,
    SubmissionLink,
    Thread,
)
from projet.models.base import utcnow
from projet.models.enums import ProgrammeStatus, SubmissionSlot
from projet.services.auth import Actor
from projet.services.messaging import (
    mark_read,
    unacknowledged,
    unread_counts,
    visible_threads,
)
from projet.services.submission import (
    SubmissionError,
    clear_link,
    is_locked,
    recheck,
    set_link,
    submission_for_participant,
)

router = APIRouter(prefix="/me", tags=["participant"])


class SlotOut(BaseModel):
    slot: str
    drive_url: str | None
    access_status: str
    filename: str | None
    message: str | None = None


class SubmissionOut(BaseModel):
    status: str
    locked: bool
    submitted_at: datetime | None
    slots: list[SlotOut]


class ThreadSummary(BaseModel):
    id: uuid.UUID
    type: str
    title: str | None
    pinned: bool
    requires_ack: bool
    acknowledged: bool
    status: str
    unread: int
    reply_count: int
    created_at: datetime


class DataPackEntry(BaseModel):
    label: str
    url: str | None
    provenance: str


class CriterionPublic(BaseModel):
    slot: int
    name: str
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None


class ProgrammeCard(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    role: str
    status: str
    problem_statement: str | None
    deliverable: str
    start_at: datetime | None
    submit_deadline_at: datetime | None
    timezone: str


class JudgingSlot(BaseModel):
    starts_at: datetime
    location_or_meet_link: str | None
    run_order: int | None


class Dashboard(BaseModel):
    """FR-501 to FR-507 — what do I do, by when, and where."""

    provisioning: bool
    programme: ProgrammeCard
    submission: SubmissionOut | None
    judging: JudgingSlot | None
    criteria: list[CriterionPublic]
    data_pack: list[DataPackEntry]
    threads: list[ThreadSummary]
    blocking_acknowledgements: list[ThreadSummary]


def _participant(db: Session, actor: Actor) -> Participant:
    """The signed-in person's current participation.

    A person can have several across cohorts; the live one wins, and the most
    recent otherwise, so a returning participant lands on what they are doing
    now rather than something from last year.
    """
    live = (
        select(Participant)
        .join(Programme, Participant.programme_id == Programme.id)
        .where(Participant.person_id == actor.id)
        .where(Programme.status.not_in([ProgrammeStatus.COMPLETE]))
        .order_by(Programme.start_at.desc().nullslast())
    )
    participant = db.scalars(live).first()
    if participant is None:
        participant = db.scalars(
            select(Participant)
            .where(Participant.person_id == actor.id)
            .order_by(Participant.created_at.desc())
        ).first()
    if participant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not on a programme yet.")
    return participant


def _thread_summary(db: Session, thread: Thread, unread: int, acknowledged: bool) -> ThreadSummary:
    from sqlalchemy import func

    replies = db.scalar(select(func.count()).select_from(Post).where(Post.thread_id == thread.id))
    return ThreadSummary(
        id=thread.id,
        type=thread.type.value,
        title=thread.title,
        pinned=bool(thread.pinned and (not thread.pinned_until or thread.pinned_until > utcnow())),
        requires_ack=thread.requires_ack,
        acknowledged=acknowledged,
        status=thread.status.value,
        unread=unread,
        reply_count=max(0, (replies or 1) - 1),
        created_at=thread.created_at,
    )


def _submission_out(db: Session, participant: Participant) -> SubmissionOut | None:
    submission = submission_for_participant(db, participant)
    if submission is None:
        return None
    links = list(
        db.scalars(
            select(SubmissionLink)
            .where(SubmissionLink.submission_id == submission.id)
            .order_by(SubmissionLink.slot)
        )
    )
    return SubmissionOut(
        status=submission.status.value,
        locked=is_locked(db, submission),
        submitted_at=submission.submitted_at,
        slots=[
            SlotOut(
                slot=link.slot.value,
                drive_url=link.drive_url,
                access_status=link.access_status.value,
                filename=link.detected_filename,
            )
            for link in links
        ],
    )


def _require_submission_out(db: Session, participant: Participant) -> SubmissionOut:
    """After a mutation the submission is known to exist; this keeps that
    guarantee explicit rather than leaving an Optional to leak into the route."""
    out = _submission_out(db, participant)
    if out is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your submission is still being set up.")
    return out


@router.get("/dashboard", response_model=Dashboard)
def dashboard(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> Dashboard:
    participant = _participant(db, actor)
    programme = db.get(Programme, participant.programme_id)
    if programme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That programme no longer exists.")
    role = db.get(Role, programme.role_id)
    template = db.get(RoleTemplate, programme.role_id)
    from projet.models import Company

    company = db.get(Company, programme.company_id)

    submission = _submission_out(db, participant)
    # FR-506 — a fresh acceptance must never see a half-configured dashboard.
    provisioning = submission is None

    judging = None
    if participant.judging_session_id:
        row = db.get(JudgingSession, participant.judging_session_id)
        if row is not None:
            judging = JudgingSlot(
                starts_at=row.starts_at,
                location_or_meet_link=row.location_or_meet_link,
                run_order=participant.run_order,
            )

    counts = unread_counts(db, participant)
    from projet.models import ThreadRead

    acks = {
        row.thread_id: row.acknowledged_at is not None
        for row in db.scalars(select(ThreadRead).where(ThreadRead.participant_id == participant.id))
    }
    threads = [
        _thread_summary(db, thread, counts.get(thread.id, 0), acks.get(thread.id, False))
        for thread in visible_threads(db, participant)
    ]
    blocking = [
        _thread_summary(db, thread, counts.get(thread.id, 0), False)
        for thread in unacknowledged(db, participant)
    ]

    criteria = db.scalars(
        select(RubricCriterion)
        .where(RubricCriterion.programme_id == participant.programme_id)
        .order_by(RubricCriterion.slot)
    )
    data_pack = db.scalars(
        select(DataPackResource).where(DataPackResource.programme_id == participant.programme_id)
    )

    return Dashboard(
        provisioning=provisioning,
        programme=ProgrammeCard(
            id=programme.id,
            title=programme.title,
            company=company.name if company else "",
            role=role.name if role else "",
            status=programme.status.value,
            problem_statement=programme.problem_statement,
            deliverable=programme.deliverable_spec
            or (template.default_deliverable if template else ""),
            start_at=programme.start_at,
            submit_deadline_at=programme.submit_deadline_at,
            # FR-501/FR-1602 — stored UTC, rendered in their timezone.
            timezone=participant.person.timezone,
        ),
        submission=submission,
        judging=judging,
        criteria=[
            CriterionPublic(
                slot=c.slot,
                name=c.name,
                anchor_5=c.anchor_5,
                anchor_3=c.anchor_3,
                anchor_1=c.anchor_1,
            )
            for c in criteria
        ],
        data_pack=[
            DataPackEntry(label=r.label, url=r.url_or_storage_key, provenance=r.provenance.value)
            for r in data_pack
        ],
        threads=threads,
        blocking_acknowledgements=blocking,
    )


class LinkRequest(BaseModel):
    slot: str = Field(pattern="^(artifact|memo|extra)$")
    drive_url: str = Field(min_length=1, max_length=2000)


@router.put("/submission/link", response_model=SubmissionOut)
def put_link(
    payload: LinkRequest,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    """FR-802 — checked the moment it is pasted, with the answer inline."""
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your submission is still being set up.")
    try:
        set_link(db, submission, SubmissionSlot(payload.slot), payload.drive_url)
    except SubmissionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _require_submission_out(db, participant)


@router.delete("/submission/link/{slot}", response_model=SubmissionOut)
def delete_link(
    slot: str,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No submission yet.")
    try:
        clear_link(db, submission, SubmissionSlot(slot))
    except (SubmissionError, ValueError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _require_submission_out(db, participant)


@router.post("/submission/recheck", response_model=SubmissionOut)
def recheck_links(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    """ "I've fixed the sharing setting" — check again without re-pasting."""
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No submission yet.")
    recheck(db, submission)
    db.commit()
    return _require_submission_out(db, participant)


@router.post("/threads/{thread_id}/read", status_code=204)
def read_thread(
    thread_id: uuid.UUID,
    acknowledge: bool = False,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> None:
    participant = _participant(db, actor)
    thread = db.get(Thread, thread_id)
    if thread is None or thread.programme_id != participant.programme_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    mark_read(db, thread, participant, acknowledge=acknowledge)
    db.commit()
