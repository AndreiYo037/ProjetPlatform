"""Ordering the skill taxonomy for the people who have to pick from it.

FR-903b — a judge with ninety seconds between pitches picks from what is in
front of them. Three hundred and fifty skills in alphabetical order is a
scroll, and a scroll under time pressure means whatever starts with "A". The
role's own ranked skills go first, because those are the ones the week was
designed to demonstrate; the rest stay reachable by typing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import RoleTemplate, Skill


@dataclass(slots=True)
class RankedSkill:
    skill: Skill
    # Whether this role's template ranks it — what the picker shows first and
    # labels, rather than leaving the judge to guess which of 350 matter here.
    suggested: bool


def options_for_roles(session: Session, role_ids: list[uuid.UUID]) -> list[RankedSkill]:
    """Every skill, ranked ones from each role first, then the rest."""
    ranked: list[str] = []
    seen: set[str] = set()
    for role_id in role_ids:
        template = session.get(RoleTemplate, role_id)
        if template is None:
            continue
        for name in [*(template.ranked_hard_skills or []), *(template.ranked_soft_skills or [])]:
            if name not in seen:
                seen.add(name)
                ranked.append(name)
    return _options_from_ranked(session, ranked)


def options_for_role(session: Session, role_id: uuid.UUID | None) -> list[RankedSkill]:
    """Every skill, the role's ranked ones first and in their ranked order."""
    template = session.get(RoleTemplate, role_id) if role_id else None
    ranked: list[str] = []
    if template is not None:
        ranked = [*(template.ranked_hard_skills or []), *(template.ranked_soft_skills or [])]
    return _options_from_ranked(session, ranked)


def _options_from_ranked(session: Session, ranked: list[str]) -> list[RankedSkill]:
    by_name = {skill.name: skill for skill in session.scalars(select(Skill))}

    ordered: list[RankedSkill] = []
    taken: set[uuid.UUID] = set()
    for name in ranked:
        skill = by_name.get(name)
        # A template naming a skill the taxonomy does not have is a seed
        # problem, not something to fail a scoring card over.
        if skill is not None and skill.id not in taken:
            taken.add(skill.id)
            ordered.append(RankedSkill(skill=skill, suggested=True))

    for skill in sorted(by_name.values(), key=lambda s: s.name):
        if skill.id not in taken:
            ordered.append(RankedSkill(skill=skill, suggested=False))
    return ordered
