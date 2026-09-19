"""The profile side of FR-903: judge tags become attested skills, and attested
skills roll up onto capabilities.

Two steps, deliberately separate:

    ScoreSkillTag  ->  ProfileSkill  ->  Capability
    (what a judge     (what the        (the axis it is
     observed)         profile says)    comparable on)

The first step is a promotion with an attester attached — it is what makes a
profile skill materially different from a self-declared one. The second is a
pure query, not a stored table: per person the volume is tiny (tens of rows),
and a denormalised rollup would drift the moment capabilities.md is edited.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Capability,
    Company,
    CompanyUser,
    Participant,
    ProfileSkill,
    Programme,
    Score,
    ScoreSkillTag,
    Skill,
    SkillCapability,
    Testimonial,
)
from projet.models.enums import SkillType


@dataclass
class SkillEvidence:
    """One attested skill, and who stands behind it."""

    skill_id: uuid.UUID
    name: str
    type: SkillType
    programme_ids: set[uuid.UUID] = field(default_factory=set)
    attesters: list[str] = field(default_factory=list)


@dataclass
class CapabilityRollup:
    name: str
    slug: str
    summary: str
    sort_order: int
    skills: list[SkillEvidence]
    programme_count: int
    attester_count: int


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


def capability_rollup(
    session: Session, person_id: uuid.UUID, *, include_hidden: bool = False
) -> list[CapabilityRollup]:
    """A person's attested skills, grouped onto the universal capabilities.

    Counts are of **distinct programmes and distinct attesters**, never of rows.
    A skill mapping onto two capabilities would otherwise make one attestation
    look like two, and a profile that inflates is worse than no profile.

    Capabilities with no evidence are omitted: an empty axis on a profile reads
    as a weakness the platform never measured.
    """
    query = (
        select(
            Capability.id,
            Capability.name,
            Capability.slug,
            Capability.summary,
            Capability.sort_order,
            Skill.id,
            Skill.name,
            Skill.type,
            ProfileSkill.programme_id,
            ProfileSkill.attested_by_name,
            ProfileSkill.attested_by_company,
        )
        .join(Skill, Skill.id == ProfileSkill.skill_id)
        .join(SkillCapability, SkillCapability.skill_id == Skill.id)
        .join(Capability, Capability.id == SkillCapability.capability_id)
        .where(ProfileSkill.person_id == person_id)
        .order_by(Capability.sort_order, Skill.name)
    )
    if not include_hidden:
        query = query.where(ProfileSkill.visible.is_(True))

    rollups: dict[uuid.UUID, CapabilityRollup] = {}
    evidence: dict[tuple[uuid.UUID, uuid.UUID], SkillEvidence] = {}
    attesters: dict[uuid.UUID, set[tuple[str | None, str | None]]] = {}

    for row in session.execute(query):
        (
            capability_id,
            capability_name,
            slug,
            summary,
            sort_order,
            skill_id,
            skill_name,
            skill_type,
            programme_id,
            attested_by_name,
            attested_by_company,
        ) = row

        rollup = rollups.get(capability_id)
        if rollup is None:
            rollup = CapabilityRollup(
                name=capability_name,
                slug=slug,
                summary=summary,
                sort_order=sort_order,
                skills=[],
                programme_count=0,
                attester_count=0,
            )
            rollups[capability_id] = rollup
            attesters[capability_id] = set()

        key = (capability_id, skill_id)
        item = evidence.get(key)
        if item is None:
            item = SkillEvidence(skill_id=skill_id, name=skill_name, type=skill_type)
            evidence[key] = item
            rollup.skills.append(item)
        item.programme_ids.add(programme_id)

        if attested_by_name and attested_by_name not in item.attesters:
            item.attesters.append(attested_by_name)
        # An attester is a person at a company. Two judges of the same name at
        # different companies are two attesters; the same judge across two
        # programmes is one.
        attesters[capability_id].add((attested_by_name, attested_by_company))

    for capability_id, rollup in rollups.items():
        rollup.programme_count = len({pid for item in rollup.skills for pid in item.programme_ids})
        rollup.attester_count = len({a for a in attesters[capability_id] if a[0]})

    return sorted(rollups.values(), key=lambda r: r.sort_order)


@dataclass
class ProgrammeEndorsement:
    """One company's attested skills from one programme — the credential."""

    company: str
    programme: str
    skills: list[str]
    attesters: list[str]


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
    for company, title, programme_id, skill, attester, _created in session.execute(query):
        card = groups.get(programme_id)
        if card is None:
            card = ProgrammeEndorsement(
                company=company, programme=title, skills=[], attesters=[]
            )
            groups[programme_id] = card
            order.append(programme_id)
        if skill not in card.skills:
            card.skills.append(skill)
        if attester and attester not in card.attesters:
            card.attesters.append(attester)
    return [groups[pid] for pid in order]


def published_testimonials_for(session: Session, person_id: uuid.UUID):
    """Published testimonials across every programme this person has done.

    Published only. A draft is a rep still thinking, and surfacing it — to the
    person it is about or to a stranger reading the public page — would make
    every draft a promise nobody chose to make yet.
    """
    return session.execute(
        select(Testimonial, CompanyUser, Company, Programme)
        .join(Participant, Participant.id == Testimonial.participant_id)
        .join(CompanyUser, CompanyUser.id == Testimonial.author_company_user_id)
        .join(Company, Company.id == CompanyUser.company_id)
        .join(Programme, Programme.id == Participant.programme_id)
        .where(Participant.person_id == person_id)
        .where(Testimonial.published_at.isnot(None))
        .order_by(Testimonial.published_at.desc())
    ).all()
