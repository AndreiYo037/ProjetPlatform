"""Submission cards and scoring cards (FR-900, FR-1051).

One card per participant, and the card links to that person's scoring card.
Everything is individual, so both are unambiguous: a judge opens the work, then
scores the person who did it, without picking anyone out of a group first.

The two are deliberately the same object seen twice. A judge on the pitch call
wants the links to hand and the anchors on screen at once, so the scoring card
carries the submission with it rather than making them hold two tabs open.

Recruitment consent (FR-020) does not hide a seated participant from judging.
Once the company admits someone, they have to score the work — consent only
gates the post-programme candidate pool and exports (FR-1101, FR-1103).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import can_score_programme, get_programme_or_404, require_actor
from projet.db import get_session
from projet.models import (
    Company,
    CompanyUser,
    CriterionScore,
    JudgingSession,
    Participant,
    Person,
    Programme,
    ScoreMember,
    ScoreSkillTag,
    Skill,
    SubmissionLink,
    Testimonial,
)
from projet.models.base import utcnow
from projet.models.enums import AccessStatus, ReferralIntent
from projet.services.auth import Actor
from projet.services.closeout import CloseoutError, close_programme
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
from projet.services.skills import options_for_roles
from projet.services.testimonial_pdf import render_testimonial_pdf
from projet.storage import get_storage, sign_key

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
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not judging this programme.")
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
    max_total: int
    pitch_at: datetime | None = None
    meet_link: str | None = None


class ScoringAnchor(BaseModel):
    slot: str
    criterion_id: uuid.UUID
    name: str
    is_universal: bool
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None
    value: int | None
    role_name: str | None = None


class SkillOption(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    # True for the skills this role's template ranks. The picker groups on it
    # so a judge sees the handful that matter here before the other 340.
    suggested: bool = False


class ScoringCard(BaseModel):
    """The rubric for this pitch, with the submission kept alongside it."""

    participant_id: uuid.UUID
    name: str
    submission: SubmissionCard
    criteria: list[ScoringAnchor]
    total: int | None
    max_total: int
    complete: bool
    would_refer: str | None
    skill_ids: list[uuid.UUID]
    skill_options: list[SkillOption]


def _participant_or_404(
    db: Session, programme: Programme, actor: Actor, participant_id: uuid.UUID
) -> Participant:
    """Any seated participant on this programme.

    Recruitment consent does not apply here: judging is part of running the
    challenge the company already admitted them to.
    """
    _ = actor  # judge gate is upstream; kept for call-site symmetry
    participant = db.scalar(
        select(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.id == participant_id)
    )
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
    slot = db.get(JudgingSession, participant.judging_session_id) if participant.judging_session_id else None
    programme = db.get(Programme, participant.programme_id)
    needed = len(criteria_for(db, participant.programme_id))
    meet = None
    if slot and slot.location_or_meet_link:
        meet = slot.location_or_meet_link
    elif programme is not None:
        meet = programme.pitch_meet_link
    return SubmissionCard(
        participant_id=participant.id,
        name=person.name if person else "",
        organisation=person.organisation if person else None,
        run_order=participant.run_order,
        status=submission.status.value if submission else "draft",
        submitted_at=submission.submitted_at if submission else None,
        locked=bool(submission and submission.locked_at),
        # Same rule as the participant dashboard: a pasted link we can open, or
        # a file we already hold. Memo is an upload, so snapshot_url is enough.
        complete=bool(links)
        and all(
            (link.url or link.snapshot_url)
            and link.access_status == AccessStatus.OK.value
            for link in links
        ),
        links=links,
        scored=score is not None,
        your_total=score.total if score else None,
        max_total=needed * 5,
        pitch_at=slot.starts_at if slot else None,
        meet_link=meet,
    )


@router.get("/programmes/{programme_id}/submissions", response_model=list[SubmissionCard])
def list_submission_cards(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> list[SubmissionCard]:
    """FR-1051 - the judging day list, in the order people pitch.

    Every non-excluded seat appears here, including people who declined
    recruitment sharing. That consent only gates the candidate pool later.
    """
    statement = (
        select(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.excluded.is_(False))
    )
    participants = list(db.scalars(statement))
    slots = {
        row.id: row
        for row in db.scalars(
            select(JudgingSession).where(JudgingSession.programme_id == programme.id)
        )
    }

    def sort_key(participant: Participant):
        row = slots.get(participant.judging_session_id) if participant.judging_session_id else None
        start = row.starts_at if row else None
        return (
            start is None,
            start or datetime.min.replace(tzinfo=UTC),
            participant.run_order is None,
            participant.run_order or 0,
            participant.created_at,
        )

    participants = sorted(participants, key=sort_key)
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
            for row in db.scalars(select(CriterionScore).where(CriterionScore.score_id == score.id))
        }

    from projet.services.rubric import display_slot, load_programme_roles, programme_role_ids

    roles = load_programme_roles(db, programme)
    by_id = {role.id: role for role in roles}
    role_count = len(programme_role_ids(db, programme))
    criteria = [
        ScoringAnchor(
            slot=display_slot(criterion, role_count),
            criterion_id=criterion.id,
            name=criterion.name,
            is_universal=criterion.is_universal,
            anchor_5=criterion.anchor_5,
            anchor_3=criterion.anchor_3,
            anchor_1=criterion.anchor_1,
            value=values.get(criterion.id),
            role_name=by_id[criterion.role_id].name if criterion.role_id in by_id else None,
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

    # The role's own ranked skills first, so the list opens as a shortlist
    # rather than an alphabetical scroll through hundreds (FR-903b).
    options = [
        SkillOption(
            id=ranked.skill.id,
            name=ranked.skill.name,
            type=ranked.skill.type.value,
            suggested=ranked.suggested,
        )
        for ranked in options_for_roles(db, [role.id for role in roles])
    ]

    return ScoringCard(
        participant_id=participant.id,
        name=person.name if person else "",
        submission=_card(db, participant, scorer_id),
        criteria=criteria,
        total=score.total if score else None,
        max_total=len(criteria) * 5,
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


# -- testimonials (FR-1053) ---------------------------------------------------
#
# Deliberately not part of the scoring card. A testimonial is a public claim the
# company is willing to put its name to; a score is a private working note. They
# are written in the same sitting and must never travel together, so the
# testimonial carries no reference to Score and reads back without one.


class TestimonialOut(BaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    body: str
    author_name: str | None
    author_title: str | None
    pdf_url: str | None
    published_at: datetime | None
    created_at: datetime


class TestimonialWrite(BaseModel):
    body: str = Field(default="", max_length=4000)
    # A draft is a real state: a rep should be able to write badly at 9pm and
    # fix it in the morning before anyone can quote it.
    publish: bool = False


def _pdf_url(key: str | None) -> str | None:
    if not key:
        return None
    return f"/files/{key}?sig={sign_key(key)}"


def _testimonial_out(db: Session, row: Testimonial) -> TestimonialOut:
    author = db.get(CompanyUser, row.author_company_user_id)
    return TestimonialOut(
        id=row.id,
        participant_id=row.participant_id,
        body=row.body,
        author_name=author.name if author else None,
        author_title=author.title if author else None,
        pdf_url=_pdf_url(row.pdf_storage_key),
        published_at=row.published_at,
        created_at=row.created_at,
    )


@router.get(
    "/programmes/{programme_id}/participants/{participant_id}/testimonial",
    response_model=TestimonialOut | None,
)
def get_testimonial(
    participant_id: uuid.UUID,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> TestimonialOut | None:
    """Your own, not your colleague's. Two reps may each write one."""
    participant = _participant_or_404(db, programme, actor, participant_id)
    if actor.is_platform:
        return None
    row = db.scalar(
        select(Testimonial)
        .where(Testimonial.participant_id == participant.id)
        .where(Testimonial.author_company_user_id == actor.id)
    )
    return _testimonial_out(db, row) if row else None


@router.put(
    "/programmes/{programme_id}/participants/{participant_id}/testimonial",
    response_model=TestimonialOut,
)
def write_testimonial(
    participant_id: uuid.UUID,
    payload: TestimonialWrite,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> TestimonialOut:
    """Optional by design (FR-1053).

    A testimonial nobody chose to write is worth more than one everybody was
    made to, so this is never required to finish scoring and never prompted for
    until a pitch has actually been watched.
    """
    if actor.is_platform:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A testimonial is the company's word. Sign in as the company user.",
        )
    participant = _participant_or_404(db, programme, actor, participant_id)
    row = db.scalar(
        select(Testimonial)
        .where(Testimonial.participant_id == participant.id)
        .where(Testimonial.author_company_user_id == actor.id)
    )
    if row is None:
        row = Testimonial(
            participant_id=participant.id,
            author_company_user_id=actor.id,
            body=payload.body.strip(),
        )
        db.add(row)
    else:
        row.body = payload.body.strip()
    # Publishing is one-way from the participant's side: they may already have
    # put it on a CV, so unpublishing would retract something in use. Editing
    # the wording stays open; we regenerate the downloadable PDF from it.
    db.flush()
    if payload.publish or row.published_at is not None:
        if not row.body:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Write the testimonial before publishing.",
            )
        _store_generated_pdf(db, row=row, participant=participant, programme=programme)
    if payload.publish and row.published_at is None:
        # PDF generated — not live on the profile, and no email,
        # until the company closes.
        row.published_at = utcnow()
    db.commit()
    return _testimonial_out(db, row)


def _store_generated_pdf(
    db: Session, *, row: Testimonial, participant: Participant, programme: Programme
) -> None:
    author = db.get(CompanyUser, row.author_company_user_id)
    company = db.get(Company, programme.company_id)
    pdf = render_testimonial_pdf(
        body=row.body,
        author_name=author.name if author else "",
        author_title=author.title if author else None,
        company_name=company.name if company else "",
        programme_title=programme.title,
    )
    key = f"testimonials/{participant.id}/{row.id}.pdf"
    get_storage().put(key, pdf, "application/pdf")
    row.pdf_storage_key = key


class TestimonialDraftOut(BaseModel):
    body: str


def _endorsed_skill_names(db: Session, participant: Participant, scorer_id: uuid.UUID) -> list[str]:
    """This judge's tags on this person, not a colleague's and not the profile."""
    team = team_for_participant(db, participant)
    if team is None:
        return []
    score = score_for(db, team, scorer_id)
    if score is None:
        return []
    return list(
        db.scalars(
            select(Skill.name)
            .join(ScoreSkillTag, ScoreSkillTag.skill_id == Skill.id)
            .where(ScoreSkillTag.score_id == score.id)
            .where(ScoreSkillTag.participant_id == participant.id)
            .order_by(Skill.name)
        )
    )


@router.post(
    "/programmes/{programme_id}/participants/{participant_id}/testimonial/draft",
    response_model=TestimonialDraftOut,
)
def draft_testimonial_endpoint(
    participant_id: uuid.UUID,
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> TestimonialDraftOut:
    """Draft from endorsed skills and the brief. Does not save or publish.

    The model only rearranges facts already on the card. A generated paragraph
    is still the company's word, so it lands in the textarea rather than on
    the profile.
    """
    from projet.integrations.claude import DraftingUnavailable, draft_testimonial

    if actor.is_platform:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A testimonial is the company's word. Sign in as the company user.",
        )
    participant = _participant_or_404(db, programme, actor, participant_id)
    skills = _endorsed_skill_names(db, participant, actor.id)
    if not skills:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Tag the skills you actually saw before drafting a testimonial.",
        )
    brief = (programme.problem_statement or "").strip()
    deliverable = (programme.deliverable_spec or "").strip()
    if not brief and not deliverable:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This challenge has no problem statement yet, so there is nothing "
            "to ground a testimonial in.",
        )

    from projet.services.rubric import load_programme_roles
    from projet.services.writeup import join_names

    person = db.get(Person, participant.person_id)
    author = db.get(CompanyUser, actor.id)
    company = db.get(Company, programme.company_id)
    roles = load_programme_roles(db, programme)
    if person is None or author is None or company is None or not roles:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme is not fully configured.")

    try:
        body = draft_testimonial(
            student_name=person.name,
            student_organisation=person.organisation,
            student_year_course=person.year_course,
            student_job_title=person.job_title,
            author_name=author.name,
            author_title=author.title,
            company_name=company.name,
            programme_title=programme.title,
            role_name=join_names([role.name for role in roles]),
            problem_statement=brief or None,
            deliverable_spec=deliverable or None,
            skill_names=skills,
        )
    except DraftingUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return TestimonialDraftOut(body=body)


# -- closing the programme ----------------------------------------------------


class CloseoutOut(BaseModel):
    status: str
    participants_closed: int
    credentials_issued: int
    skills_promoted: int
    # Participants no judge scored. Named rather than silently skipped: an
    # unscored pitch is usually somebody forgetting to finish a card, and that
    # is fixable right up until the programme closes.
    unscored: int


@router.post("/programmes/{programme_id}/close", response_model=CloseoutOut)
def close(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_judge),
) -> CloseoutOut:
    """Turn the evening's scores into the thing participants keep.

    Once. A second close is refused.
    """
    try:
        result = close_programme(db, programme)
    except CloseoutError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return CloseoutOut(
        status=programme.status.value,
        participants_closed=result.participants_closed,
        credentials_issued=result.credentials_issued,
        skills_promoted=result.skills_promoted,
        unscored=len(result.skipped),
    )
