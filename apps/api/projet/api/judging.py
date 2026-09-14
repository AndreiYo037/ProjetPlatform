"""Submission cards and scoring cards (FR-900, FR-1051).

One card per participant, and the card links to that person's scoring card.
Everything is individual, so both are unambiguous: a judge opens the work, then
scores the person who did it, without picking anyone out of a group first.

The two are deliberately the same object seen twice. A judge on the pitch call
wants the links to hand and the anchors on screen at once, so the scoring card
carries the submission with it rather than making them hold two tabs open.

Consent is enforced at the query layer as everywhere else: the cards come from
`company_visible_submissions`, so a participant who declined sharing is not in
the list a company sees. Platform staff see the cohort whole.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.access import company_visible_participants
from projet.api.deps import can_score_programme, get_programme_or_404, require_actor
from projet.db import get_session
from projet.models import (
    CriterionScore,
    Participant,
    Person,
    Programme,
    ScoreMember,
    ScoreSkillTag,
    Skill,
    SubmissionLink,
)
from projet.models.enums import AccessStatus, ReferralIntent
from projet.services.auth import Actor
from projet.services.scoring import (
    ScoringError,
    criteria_for,
    ensure_score,
    record_criterion,
    refresh_total,
    score_for,
    set_referral,
    set_skill_tags,
    submission_for,
    team_for_participant,
)
from projet.storage import sign_key

router = APIRouter(tags=["judging"])


def require_judge(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> Actor:
    """Whoever may look at this pitch.

    A company user with scoring rights on the programme, or platform staff. An
    unassigned rep and a participant both fail here, which is FR-015 and FR-1004
    resolving to the same check rather than two.
    """
    if not can_score_programme(db, actor, programme):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You are not judging this programme."
        )
    return actor


class SubmittedLink(BaseModel):
    slot: str
    url: str | None
    filename: str | None
    access_status: str
    # What the judge should actually open. The live document can be edited after
    # the deadline; the snapshot is the copy taken at 23:59 (FR-804).
    snapshot_url: str | None = None
    snapshot_at: datetime | None = None


class SubmissionCard(BaseModel):
    """One participant, what they handed in, and where their scoring stands."""

    participant_id: uuid.UUID
    name: str
    organisation: str | None
    run_order: int | None
    status: str
    submitted_at: datetime | None
    locked: bool
    complete: bool
    links: list[SubmittedLink]
    # Your own card, not the cohort's. A judge comparing against someone else's
    # in-progress total is the failure mode calibration is supposed to prevent.
    scored: bool
    your_total: int | None


class ScoringAnchor(BaseModel):
    slot: int
    criterion_id: uuid.UUID
    name: str
    is_universal: bool
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None
    value: int | None


class SkillOption(BaseModel):
    id: uuid.UUID
    name: str
    type: str


class ScoringCard(BaseModel):
    """The rubric for this pitch, with the submission kept alongside it."""

    participant_id: uuid.UUID
    name: str
    submission: SubmissionCard
    criteria: list[ScoringAnchor]
    total: int | None
    complete: bool
    would_refer: str | None
    skill_ids: list[uuid.UUID]
    skill_options: list[SkillOption]


def _participant_or_404(
    db: Session, programme: Programme, actor: Actor, participant_id: uuid.UUID
) -> Participant:
    """Scoped by consent for a company, whole for platform staff.

    404 rather than 403, so a company cannot learn that someone is in the cohort
    by being refused their card.
    """
    statement = (
        select(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.id == participant_id)
    )
    if not actor.is_platform:
        statement = company_visible_participants(programme.id).where(
            Participant.id == participant_id
        )
    participant = db.scalar(statement)
    if participant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such participant.")
    return participant


def _card(db: Session, participant: Participant, scorer_id: uuid.UUID | None) -> SubmissionCard:
    person = db.get(Person, participant.person_id)
    team = team_for_participant(db, participant)
    submission = submission_for(db, team) if team else None

    links: list[SubmittedLink] = []
    if submission is not None:
        rows = db.scalars(
            select(SubmissionLink)
            .where(SubmissionLink.submission_id == submission.id)
            .order_by(SubmissionLink.slot)
        )
        for row in rows:
            snapshot_url = None
            if row.snapshot_key:
                # Section 8 - a snapshot is not publicly addressable, the same
                # as a CV. Signed here so the link expires with the sitting.
                snapshot_url = f"/files/{row.snapshot_key}?sig={sign_key(row.snapshot_key)}"
            links.append(
                SubmittedLink(
                    slot=row.slot.value,
                    url=row.drive_url,
                    filename=row.detected_filename,
                    access_status=row.access_status.value,
                    snapshot_url=snapshot_url,
                    snapshot_at=row.snapshot_at,
                )
            )

    score = score_for(db, team, scorer_id) if team and scorer_id else None
    return SubmissionCard(
        participant_id=participant.id,
        name=person.name if person else "",
        organisation=person.organisation if person else None,
        run_order=participant.run_order,
        status=submission.status.value if submission else "draft",
        submitted_at=submission.submitted_at if submission else None,
        locked=bool(submission and submission.locked_at),
        # The same definition services/submission uses: every named slot filled
        # with something we can actually open. A card that says complete while a
        # memo slot is empty would send a judge into a pitch with half the work.
        complete=bool(links)
        and all(
            link.url and link.access_status == AccessStatus.OK.value for link in links
        ),
        links=links,
        scored=score is not None,
        your_total=score.total if score else None,
    )


@router.get("/programmes/{programme_id}/submissions", response_model=list[SubmissionCard])
def list_submission_cards(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> list[SubmissionCard]:
    """FR-1051 - the judging day list, in the order people pitch."""
    statement = select(Participant).where(Participant.programme_id == programme.id)
    if not actor.is_platform:
        statement = company_visible_participants(programme.id)
    participants = sorted(
        db.scalars(statement.where(Participant.excluded.is_(False))),
        key=lambda p: (p.run_order is None, p.run_order or 0, p.created_at),
    )
    scorer_id = None if actor.is_platform else actor.id
    return [_card(db, participant, scorer_id) for participant in participants]


def _scoring_card(db: Session, programme: Programme, participant: Participant, actor: Actor):
    person = db.get(Person, participant.person_id)
    team = team_for_participant(db, participant)
    scorer_id = None if actor.is_platform else actor.id
    score = score_for(db, team, scorer_id) if team and scorer_id else None

    values: dict[uuid.UUID, int] = {}
    if score is not None:
        values = {
            row.criterion_id: row.value
            for row in db.scalars(
                select(CriterionScore).where(CriterionScore.score_id == score.id)
            )
        }

    criteria = [
        ScoringAnchor(
            slot=criterion.slot,
            criterion_id=criterion.id,
            name=criterion.name,
            is_universal=criterion.is_universal,
            anchor_5=criterion.anchor_5,
            anchor_3=criterion.anchor_3,
            anchor_1=criterion.anchor_1,
            value=values.get(criterion.id),
        )
        for criterion in criteria_for(db, programme.id)
    ]

    referral = None
    skill_ids: list[uuid.UUID] = []
    if score is not None:
        member = db.scalar(
            select(ScoreMember)
            .where(ScoreMember.score_id == score.id)
            .where(ScoreMember.participant_id == participant.id)
        )
        referral = member.would_refer.value if member and member.would_refer else None
        skill_ids = list(
            db.scalars(
                select(ScoreSkillTag.skill_id)
                .where(ScoreSkillTag.score_id == score.id)
                .where(ScoreSkillTag.participant_id == participant.id)
            )
        )

    # The role's own ranked skills, so the list is a shortlist rather than an
    # alphabetical scroll through hundreds (FR-903b).
    options = [
        SkillOption(id=skill.id, name=skill.name, type=skill.type.value)
        for skill in db.scalars(select(Skill).order_by(Skill.name))
    ]

    return ScoringCard(
        participant_id=participant.id,
        name=person.name if person else "",
        submission=_card(db, participant, scorer_id),
        criteria=criteria,
        total=score.total if score else None,
        complete=all(criterion.value is not None for criterion in criteria) and bool(criteria),
        would_refer=referral,
        skill_ids=skill_ids,
        skill_options=options,
    )


@router.get(
    "/programmes/{programme_id}/participants/{participant_id}/score",
    response_model=ScoringCard,
)
def get_scoring_card(
    participant_id: uuid.UUID,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> ScoringCard:
    participant = _participant_or_404(db, programme, actor, participant_id)
    return _scoring_card(db, programme, participant, actor)


class ScoringUpdate(BaseModel):
    """Partial by design: a judge fills this in a value at a time, live."""

    ratings: dict[uuid.UUID, int] = Field(default_factory=dict)
    would_refer: str | None = None
    skill_ids: list[uuid.UUID] | None = None


@router.patch(
    "/programmes/{programme_id}/participants/{participant_id}/score",
    response_model=ScoringCard,
)
def update_scoring_card(
    participant_id: uuid.UUID,
    payload: ScoringUpdate,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> ScoringCard:
    """Auto-saving, like the prescreen rubric. A judge is watching a pitch, not
    filling in a form, so nothing waits on a Save they will forget to press."""
    if actor.is_platform:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Scores belong to the judge who gave them. Sign in as the company user.",
        )
    participant = _participant_or_404(db, programme, actor, participant_id)
    team = team_for_participant(db, participant)
    if team is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That participant has no submission yet.")

    score = ensure_score(db, team, actor.id)
    by_id = {criterion.id: criterion for criterion in criteria_for(db, programme.id)}
    try:
        for criterion_id, value in payload.ratings.items():
            criterion = by_id.get(criterion_id)
            if criterion is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "That criterion is not on this programme's rubric.",
                )
            record_criterion(db, score, criterion, value)
        if payload.would_refer is not None:
            intent = ReferralIntent(payload.would_refer) if payload.would_refer else None
            set_referral(db, score, participant, intent)
        if payload.skill_ids is not None:
            set_skill_tags(db, score, participant, payload.skill_ids)
    except ScoringError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown referral verdict."
        ) from error

    refresh_total(db, score)
    db.commit()
    return _scoring_card(db, programme, participant, actor)
