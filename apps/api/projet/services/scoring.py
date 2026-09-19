"""Pitch scoring (FR-900).

One judge, one card, one participant. Everything is individual now, so a Score
resolves through the participant's own team and there is exactly one of each -
which is what lets the submission card link straight to the scoring card rather
than making a judge pick a person out of a group first.

A score is written the way a judge actually works: a value at a time, while
someone is still talking. So this is an upsert over partial input rather than a
submit, the total recomputes only once all four criteria carry a value, and a
card with two of four filled in is a legitimate state rather than an error.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    CriterionScore,
    Participant,
    RubricCriterion,
    Score,
    ScoreMember,
    ScoreSkillTag,
    Skill,
    Submission,
    Team,
    TeamMember,
)
from projet.models.base import utcnow
from projet.models.enums import ReferralIntent, ScorerType

CRITERIA_PER_PROGRAMME = 4


class ScoringError(RuntimeError):
    pass


def team_for_participant(db: Session, participant: Participant) -> Team | None:
    return db.scalar(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.participant_id == participant.id)
    )


def submission_for(db: Session, team: Team) -> Submission | None:
    return db.scalar(select(Submission).where(Submission.team_id == team.id))


def criteria_for(db: Session, programme_id: uuid.UUID) -> list[RubricCriterion]:
    return list(
        db.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.programme_id == programme_id)
            .order_by(RubricCriterion.slot)
        )
    )


def score_for(db: Session, team: Team, scorer_id: uuid.UUID) -> Score | None:
    """A judge's own card. Two judges on one pitch keep two separate scores."""
    return db.scalar(
        select(Score).where(Score.team_id == team.id).where(Score.scorer_id == scorer_id)
    )


def ensure_score(
    db: Session, team: Team, scorer_id: uuid.UUID, scorer_type: ScorerType = ScorerType.REP
) -> Score:
    score = score_for(db, team, scorer_id)
    if score is None:
        score = Score(team_id=team.id, scorer_id=scorer_id, scorer_type=scorer_type)
        db.add(score)
        db.flush()
    return score


def record_criterion(db: Session, score: Score, criterion: RubricCriterion, value: int) -> None:
    """One rating. Refused outside 1-5 rather than clamped: a 7 is a mistake,
    and silently storing a 5 hides it from the person who made it."""
    if not 1 <= value <= 5:
        raise ScoringError("A rating is 1 to 5.")
    existing = db.scalar(
        select(CriterionScore)
        .where(CriterionScore.score_id == score.id)
        .where(CriterionScore.criterion_id == criterion.id)
    )
    if existing is None:
        db.add(CriterionScore(score_id=score.id, criterion_id=criterion.id, value=value))
    else:
        existing.value = value
    db.flush()


def refresh_total(db: Session, score: Score) -> None:
    """Null until the card is whole.

    A running total over two of four criteria would be ranked against a
    complete one, and the half-scored pitch would lose on arithmetic rather
    than on the work.
    """
    values = list(
        db.scalars(select(CriterionScore.value).where(CriterionScore.score_id == score.id))
    )
    score.total = sum(values) if len(values) == CRITERIA_PER_PROGRAMME else None
    score.updated_at = utcnow()


def set_referral(
    db: Session, score: Score, participant: Participant, intent: ReferralIntent | None
) -> None:
    """FR-904b — the verdict on the person, never visible to them."""
    member = db.scalar(
        select(ScoreMember)
        .where(ScoreMember.score_id == score.id)
        .where(ScoreMember.participant_id == participant.id)
    )
    if member is None:
        member = ScoreMember(score_id=score.id, participant_id=participant.id)
        db.add(member)
    member.would_refer = intent
    db.flush()


def set_skill_tags(
    db: Session, score: Score, participant: Participant, skill_ids: list[uuid.UUID]
) -> None:
    """FR-903 — replace wholesale, because the card sends the whole selection.

    A tag naming a skill that does not exist is refused rather than dropped: a
    silently discarded tag reads on the profile as a judge who saw nothing.
    """
    wanted = set(skill_ids)
    if wanted:
        known = set(db.scalars(select(Skill.id).where(Skill.id.in_(wanted))))
        missing = wanted - known
        if missing:
            raise ScoringError(f"No such skill: {sorted(str(m) for m in missing)[0]}.")
    existing = db.scalars(
        select(ScoreSkillTag)
        .where(ScoreSkillTag.score_id == score.id)
        .where(ScoreSkillTag.participant_id == participant.id)
    )
    for tag in existing:
        if tag.skill_id not in wanted:
            db.delete(tag)
        else:
            wanted.discard(tag.skill_id)
    for skill_id in wanted:
        db.add(
            ScoreSkillTag(score_id=score.id, participant_id=participant.id, skill_id=skill_id)
        )
    db.flush()
