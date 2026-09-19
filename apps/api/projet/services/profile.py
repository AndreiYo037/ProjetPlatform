"""The profile side of FR-903: judge tags become attested skills.

    ScoreSkillTag  ->  ProfileSkill
    (what a judge     (what the
     observed)         profile says)

The promotion carries an attester, which is the whole difference between this
and a skill somebody typed about themselves.

The profile lists those skills flat, one row per skill. It deliberately does
not group them onto capability axes: a skill mapping onto two capabilities
would then appear under both headings, and one judge's single tag would read
as two endorsements. The Capability/SkillCapability tables still exist for the
taxonomy and its seeding — they are simply not what a profile is built out of.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Company,
    CompanyUser,
    Participant,
    ProfileSkill,
    Programme,
    Score,
    ScoreSkillTag,
    Skill,
    Testimonial,
)
from projet.models.enums import ProgrammeStatus, SkillType


@dataclass
class SkillEvidence:
    """One attested skill, and who stands behind it."""

    skill_id: uuid.UUID
    name: str
    type: SkillType
    programme_ids: set[uuid.UUID] = field(default_factory=set)
    attesters: list[str] = field(default_factory=list)


@dataclass
class AttestedEvidence:
    """Everything a profile says about what practitioners saw.

    Counts are of distinct attesters and distinct programmes, never of rows:
    one judge tagging four skills is one attester, and a profile that inflates
    is worse than no profile.
    """

    skills: list[SkillEvidence]
    attester_count: int
    programme_count: int


def promote_score_skill_tags(session: Session, participant_id: uuid.UUID) -> int:
    """Turn a participant's judge tags into ProfileSkill rows. Returns how many
    were created; safe to re-run.

    ProfileSkill is unique on (person, programme, skill), so a skill two judges
    both tagged is one line on the profile rather than two. The earliest score
    supplies the attestation — an arbitrary but stable choice, so a re-run after
    a third judge scores does not rewrite who the profile credits.
    """
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError(f"no participant {participant_id}")

    rows = session.execute(
        select(ScoreSkillTag.skill_id, CompanyUser.name, CompanyUser.title, Company.name)
        .join(Score, Score.id == ScoreSkillTag.score_id)
        .join(CompanyUser, CompanyUser.id == Score.scorer_id)
        .join(Company, Company.id == CompanyUser.company_id)
        .where(ScoreSkillTag.participant_id == participant_id)
        .order_by(Score.created_at, Score.id)
    ).all()

    existing = {
        row.skill_id
        for row in session.scalars(
            select(ProfileSkill).where(
                ProfileSkill.person_id == participant.person_id,
                ProfileSkill.programme_id == participant.programme_id,
            )
        )
    }

    created = 0
    for skill_id, scorer_name, scorer_title, company_name in rows:
        if skill_id in existing:
            continue
        session.add(
            ProfileSkill(
                person_id=participant.person_id,
                programme_id=participant.programme_id,
                skill_id=skill_id,
                attested_by_name=scorer_name,
                attested_by_title=scorer_title,
                attested_by_company=company_name,
            )
        )
        existing.add(skill_id)
        created += 1

    session.flush()
    return created


def sync_profile_skills_from_tags(session: Session, participant_id: uuid.UUID) -> int:
    """Keep the profile in lockstep with what judges have tagged.

    The scoring card says a tag is a claim on the profile. Waiting until
    closeout left the home page empty after a company had already tagged
    someone. Closeout still re-runs promotion for anything a late score added.
    """
    created = promote_score_skill_tags(session, participant_id)
    participant = session.get(Participant, participant_id)
    if participant is None:
        return created

    tagged = set(
        session.scalars(
            select(ScoreSkillTag.skill_id).where(
                ScoreSkillTag.participant_id == participant_id
            )
        )
    )
    for row in session.scalars(
        select(ProfileSkill).where(
            ProfileSkill.person_id == participant.person_id,
            ProfileSkill.programme_id == participant.programme_id,
        )
    ):
        if row.skill_id not in tagged:
            session.delete(row)
    session.flush()
    return created


def sync_person_skills_from_tags(session: Session, person_id: uuid.UUID) -> int:
    """Promote every judge tag this person has, across programmes.

    Home and the public profile read ProfileSkill. Tags saved before that
    promotion ran on every score write still live only on ScoreSkillTag;
    opening the page has to catch them up or the participant sees nothing.
    """
    created = 0
    for participant_id in session.scalars(
        select(Participant.id).where(Participant.person_id == person_id)
    ):
        created += sync_profile_skills_from_tags(session, participant_id)
    return created


def attested_skills(
    session: Session, person_id: uuid.UUID, *, include_hidden: bool = False
) -> AttestedEvidence:
    """A person's attested skills, one row per skill.

    Strongest evidence first — most attesters, then most programmes, then
    alphabetically — because a reader scanning this stops after a few lines and
    the ones with the most people behind them are the ones worth reading.
    """
    query = (
        select(
            Skill.id,
            Skill.name,
            Skill.type,
            ProfileSkill.programme_id,
            ProfileSkill.attested_by_name,
            ProfileSkill.attested_by_company,
        )
        .join(Skill, Skill.id == ProfileSkill.skill_id)
        .where(ProfileSkill.person_id == person_id)
        .order_by(Skill.name)
    )
    if not include_hidden:
        query = query.where(ProfileSkill.visible.is_(True))

    evidence: dict[uuid.UUID, SkillEvidence] = {}
    # An attester is a person at a company. Two judges of the same name at
    # different companies are two attesters; the same judge across two
    # programmes is one.
    attesters: set[tuple[str | None, str | None]] = set()
    programmes: set[uuid.UUID] = set()

    for skill_id, name, skill_type, programme_id, attested_by, company in session.execute(query):
        item = evidence.get(skill_id)
        if item is None:
            item = SkillEvidence(skill_id=skill_id, name=name, type=skill_type)
            evidence[skill_id] = item
        item.programme_ids.add(programme_id)
        if attested_by and attested_by not in item.attesters:
            item.attesters.append(attested_by)

        programmes.add(programme_id)
        if attested_by:
            attesters.add((attested_by, company))

    # Attester order otherwise comes out of the join, which is not stable
    # between requests — the same profile would reorder its own names.
    for item in evidence.values():
        item.attesters.sort()

    skills = sorted(
        evidence.values(),
        key=lambda item: (-len(item.attesters), -len(item.programme_ids), item.name),
    )
    return AttestedEvidence(
        skills=skills,
        attester_count=len(attesters),
        programme_count=len(programmes),
    )


@dataclass
class ProgrammeEndorsement:
    """One company's attested skills from one programme — the credential."""

    company: str
    programme: str
    skills: list[str]
    attesters: list[str]
    start_at: datetime | None
    ended_at: datetime | None


def endorsements_for(
    session: Session, person_id: uuid.UUID, *, include_hidden: bool = False
) -> list[ProgrammeEndorsement]:
    """ProfileSkill rows, grouped by the programme they were earned on.

    This is what a credential is: a named company stood behind these skills
    after watching this person work, on this programme. Not a completion
    stamp, and not a code.
    """
    query = (
        select(
            Company.name,
            Programme.title,
            Programme.id,
            Programme.start_at,
            Programme.submit_deadline_at,
            Skill.name,
            ProfileSkill.attested_by_name,
            ProfileSkill.created_at,
        )
        .select_from(ProfileSkill)
        .join(Skill, Skill.id == ProfileSkill.skill_id)
        .join(Programme, Programme.id == ProfileSkill.programme_id)
        .join(Company, Company.id == Programme.company_id)
        .where(ProfileSkill.person_id == person_id)
        .order_by(ProfileSkill.created_at.desc(), Skill.name)
    )
    if not include_hidden:
        query = query.where(ProfileSkill.visible.is_(True))

    groups: dict[uuid.UUID, ProgrammeEndorsement] = {}
    order: list[uuid.UUID] = []
    for (
        company,
        title,
        programme_id,
        start_at,
        ended_at,
        skill,
        attester,
        _created,
    ) in session.execute(query):
        card = groups.get(programme_id)
        if card is None:
            card = ProgrammeEndorsement(
                company=company,
                programme=title,
                skills=[],
                attesters=[],
                start_at=start_at,
                ended_at=ended_at,
            )
            groups[programme_id] = card
            order.append(programme_id)
        if skill not in card.skills:
            card.skills.append(skill)
        if attester and attester not in card.attesters:
            card.attesters.append(attester)
    return [groups[pid] for pid in order]


def published_testimonials_for(session: Session, person_id: uuid.UUID):
    """Ready testimonials from programmes that have been closed.

    The company finishes the wording during judging. Close and issue is when
    it lands on the profile.
    """
    return session.execute(
        select(Testimonial, CompanyUser, Company, Programme)
        .join(Participant, Participant.id == Testimonial.participant_id)
        .join(CompanyUser, CompanyUser.id == Testimonial.author_company_user_id)
        .join(Company, Company.id == CompanyUser.company_id)
        .join(Programme, Programme.id == Participant.programme_id)
        .where(Participant.person_id == person_id)
        .where(Testimonial.published_at.isnot(None))
        .where(Testimonial.pdf_storage_key.isnot(None))
        .where(Programme.status == ProgrammeStatus.COMPLETE)
        .order_by(Testimonial.published_at.desc())
    ).all()
