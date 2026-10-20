"""Certificates: plan, issue, list, and the participant's own.

Planning reads only and shows the company exactly who would get which title.
Issuing writes the certificate and its PDF; asking again re-issues the same
certificate, which is how a name or a placing is corrected.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import get_programme_or_404, require_participant
from projet.api.judging import require_judge
from projet.db import get_session
from projet.models import Certificate, Company, Participant, Person, Programme, TeamMember
from projet.models.enums import ProgrammeStatus
from projet.outbox.profile_effects import notify_certificate
from projet.services.auth import Actor
from projet.services.certificates import (
    Planned,
    TeamAward,
    issue_certificates,
    plan_certificates,
)
from projet.services.scoring import team_for_participant
from projet.storage import sign_key

router = APIRouter(tags=["certificates"])


class TeamAwardIn(BaseModel):
    participant_id: uuid.UUID = Field(description="Any member of the team")
    names: list[str] | None = Field(default=None, max_length=8)
    extra_participant_ids: list[uuid.UUID] = Field(default_factory=list, max_length=8)
    tier: Literal["merit", "completion"] | None = None
    place_label: str | None = Field(default=None, max_length=40)


class PlanRequest(BaseModel):
    teams: list[TeamAwardIn] = Field(default_factory=list, max_length=100)
    applied_teams: int | None = Field(default=None, ge=0, le=10000)
    submitted_teams: int | None = Field(default=None, ge=0, le=10000)
    event_name: str | None = Field(default=None, max_length=120)
    event_date: str | None = Field(default=None, max_length=40)


class PlannedOut(BaseModel):
    team_id: uuid.UUID
    names: list[str]
    tier: str
    place_label: str | None
    rank: int
    joint: bool
    entries: int
    # The company's own scoring, shown to the company so it can check the plan.
    share_pct: float
    applied_teams: int
    submitted_teams: int


class IssuedOut(BaseModel):
    team_id: uuid.UUID
    names: list[str]
    tier: str
    place_label: str | None
    pdf_url: str | None
    issued_at: datetime


class MyCertificateOut(BaseModel):
    """What the participant sees. No rank and no score: the certificate itself
    says what it says."""

    programme: str
    company: str
    tier: str
    place_label: str | None
    names: list[str]
    pdf_url: str | None
    issued_at: datetime


class NotifyRequest(BaseModel):
    dry_run: bool = False
    # Only the participant(s) who are on the team itself, the one who submitted,
    # and not teammates added to the certificate or a second account.
    submitter_only: bool = False


class NotifyOut(BaseModel):
    # Names of the people who are (or, on a dry run, would be) emailed.
    recipients: list[str]
    queued: int
    # True once the email carries the PDF as an attachment. Lets a caller tell
    # this version of the API from the one that linked to the profile.
    attached: bool = True


def _title(row: Certificate) -> str:
    base = "Certificate of Merit" if row.tier == "merit" else "Certificate of Completion"
    return f"{base}, {row.place_label}" if row.place_label else base


def _pdf_url(key: str | None) -> str | None:
    return f"/files/{key}?sig={sign_key(key)}" if key else None


def _planned_out(plan: Planned) -> PlannedOut:
    return PlannedOut(
        team_id=plan.team_id,
        names=plan.names,
        tier=plan.tier,
        place_label=plan.place_label,
        rank=plan.rank,
        joint=plan.joint,
        entries=plan.entries,
        share_pct=round(plan.share * 100, 1),
        applied_teams=plan.applied_teams,
        submitted_teams=plan.submitted_teams,
    )


def _awards(db: Session, programme: Programme, payload: PlanRequest) -> dict[uuid.UUID, TeamAward]:
    awards: dict[uuid.UUID, TeamAward] = {}
    for item in payload.teams:
        participant = db.scalar(
            select(Participant)
            .where(Participant.programme_id == programme.id)
            .where(Participant.id == item.participant_id)
        )
        if participant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such participant.")
        team = team_for_participant(db, participant)
        if team is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That participant has no team.")
        awards[team.id] = TeamAward(
            names=item.names,
            extra_participant_ids=list(item.extra_participant_ids),
            tier=item.tier,
            place_label=item.place_label,
        )
    return awards


def _require_closed(programme: Programme, actor: Actor) -> None:
    if actor.is_platform:
        return
    if programme.status != ProgrammeStatus.COMPLETE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Certificates are issued once the challenge is closed.",
        )


@router.post("/programmes/{programme_id}/certificates/plan", response_model=list[PlannedOut])
def plan(
    payload: PlanRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> list[PlannedOut]:
    """Who would get which title. Writes nothing."""
    plans = plan_certificates(
        db,
        programme,
        awards=_awards(db, programme, payload),
        applied_teams=payload.applied_teams,
        submitted_teams=payload.submitted_teams,
    )
    return [_planned_out(p) for p in plans]


@router.post("/programmes/{programme_id}/certificates/issue", response_model=list[IssuedOut])
def issue(
    payload: PlanRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> list[IssuedOut]:
    _require_closed(programme, actor)
    plans = plan_certificates(
        db,
        programme,
        awards=_awards(db, programme, payload),
        applied_teams=payload.applied_teams,
        submitted_teams=payload.submitted_teams,
    )
    rows = issue_certificates(
        db, programme, plans, event_name=payload.event_name, event_date=payload.event_date
    )
    db.commit()
    return [
        IssuedOut(
            team_id=row.team_id,
            names=row.names,
            tier=row.tier,
            place_label=row.place_label,
            pdf_url=_pdf_url(row.pdf_storage_key),
            issued_at=row.issued_at,
        )
        for row in rows
    ]


@router.post("/programmes/{programme_id}/certificates/notify", response_model=NotifyOut)
def notify(
    payload: NotifyRequest,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> NotifyOut:
    """Tell each person on a certificate that it is ready.

    One email per person per issued certificate: asking again for the same
    issue queues nothing new, and re-issuing a certificate is a new issue.
    """
    _require_closed(programme, actor)
    company = db.get(Company, programme.company_id)
    company_name = company.name if company else "the company"
    recipients: list[str] = []
    queued = 0
    for row in db.scalars(select(Certificate).where(Certificate.programme_id == programme.id)):
        if not row.pdf_storage_key:
            continue
        allowed = (
            {
                str(pid)
                for pid in db.scalars(
                    select(Participant.person_id)
                    .join(TeamMember, TeamMember.participant_id == Participant.id)
                    .where(TeamMember.team_id == row.team_id)
                )
            }
            if payload.submitter_only
            else None
        )
        for person_id in row.recipient_person_ids or []:
            if allowed is not None and person_id not in allowed:
                continue
            person = db.get(Person, uuid.UUID(person_id))
            if person is None or not person.contact_email:
                continue
            recipients.append(person.name)
            if payload.dry_run:
                continue
            participant = db.scalar(
                select(Participant)
                .where(Participant.programme_id == programme.id)
                .where(Participant.person_id == person.id)
            )
            first = person.name.split()[0] if person.name else "there"
            who = "your team" if len(row.names) > 1 else "you"
            where = f" at {row.event_name}" if row.event_name else ""
            paragraphs = [
                f"Congratulations! {company_name} has awarded {who} a {_title(row)} for "
                f"\u201c{programme.title}\u201d{where}.",
                "Your certificate is attached as a PDF."
                + (
                    f" It carries everyone on your team ({', '.join(row.names)}), "
                    "so please pass it on to your teammates."
                    if len(row.names) > 1
                    else ""
                ),
                f"Thank you for taking part, {first}.",
            ]
            notify_certificate(
                db,
                person=person,
                participant_id=participant.id if participant else None,
                subject=f"Your {_title(row)} from {company_name}",
                paragraphs=paragraphs,
                attachment_key=row.pdf_storage_key,
                attachment_name=f"{_title(row).replace(', ', ' - ')} - {', '.join(row.names)}.pdf",
                key_suffix=f"certificate:{row.id}:{row.issued_at.isoformat()}",
            )
            queued += 1
    if not payload.dry_run:
        db.commit()
    return NotifyOut(recipients=recipients, queued=queued)


@router.get("/programmes/{programme_id}/certificates", response_model=list[IssuedOut])
def list_issued(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> list[IssuedOut]:
    rows = db.scalars(select(Certificate).where(Certificate.programme_id == programme.id))
    return [
        IssuedOut(
            team_id=row.team_id,
            names=row.names,
            tier=row.tier,
            place_label=row.place_label,
            pdf_url=_pdf_url(row.pdf_storage_key),
            issued_at=row.issued_at,
        )
        for row in rows
    ]


@router.get("/me/certificates", response_model=list[MyCertificateOut])
def my_certificates(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> list[MyCertificateOut]:
    person = db.get(Person, actor.id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    out: list[MyCertificateOut] = []
    for row in db.scalars(select(Certificate).order_by(Certificate.issued_at.desc())):
        if str(person.id) not in (row.recipient_person_ids or []):
            continue
        programme = db.get(Programme, row.programme_id)
        company = db.get(Company, programme.company_id) if programme else None
        out.append(
            MyCertificateOut(
                programme=programme.title if programme else "",
                company=company.name if company else "",
                tier=row.tier,
                place_label=row.place_label,
                names=row.names,
                pdf_url=_pdf_url(row.pdf_storage_key),
                issued_at=row.issued_at,
            )
        )
    return out
