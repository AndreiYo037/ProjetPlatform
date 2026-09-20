"""Rubric composition and the invariants that keep scores comparable (FR-070).

Criteria are data, not code. This module is the only place that writes
RubricCriterion rows, because the rules about which slots may change and when
are not expressible as database constraints.

A challenge can cover more than one role. Family 1 (problem understanding) and
family 4 (defence) sit once. Families 2 and 3 repeat for every role, shown as
2a/2b and 3a/3b when there is more than one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import Programme, ProgrammeRole, Role, RoleTemplate, RubricCriterion
from projet.models.enums import ProgrammeStatus
from projet.seeds.parsers import parse_universal_rubric

UNIVERSAL_FAMILIES = (1, 4)
# Once a programme reaches judging, editing a rubric would invalidate scores
# already entered against it (FR-076).
FROZEN_STATUSES = (ProgrammeStatus.JUDGING, ProgrammeStatus.COMPLETE)


class RubricError(RuntimeError):
    pass


@dataclass(frozen=True)
class UniversalCriterion:
    slot: int
    name: str
    anchor_5: str
    anchor_3: str
    anchor_1: str


_universal_cache: tuple[UniversalCriterion, ...] | None = None


def universal_criteria(content_dir: Path | None = None) -> tuple[UniversalCriterion, ...]:
    """Families 1 and 4, read from the same rubrics.md the roles come from."""
    global _universal_cache
    if _universal_cache is None or content_dir is not None:
        from projet.config import get_settings

        root = Path(content_dir or get_settings().content_dir)
        specs = parse_universal_rubric(root / "rubrics.md")
        criteria = tuple(
            UniversalCriterion(
                slot=s.slot,
                name=s.name,
                anchor_5=s.anchor_5,
                anchor_3=s.anchor_3,
                anchor_1=s.anchor_1,
            )
            for s in sorted(specs, key=lambda s: s.slot)
        )
        if content_dir is not None:
            return criteria
        _universal_cache = criteria
    return _universal_cache


def programme_role_ids(session: Session, programme: Programme) -> list[uuid.UUID]:
    rows = list(
        session.scalars(
            select(ProgrammeRole)
            .where(ProgrammeRole.programme_id == programme.id)
            .order_by(ProgrammeRole.position)
        )
    )
    if rows:
        return [row.role_id for row in rows]
    return [programme.role_id]


def load_programme_roles(session: Session, programme: Programme) -> list[Role]:
    roles: list[Role] = []
    for role_id in programme_role_ids(session, programme):
        role = session.get(Role, role_id)
        if role is not None:
            roles.append(role)
    return roles


def set_programme_roles(
    session: Session, programme: Programme, role_ids: list[uuid.UUID]
) -> None:
    """Replace the role list. Draft only — adding a role appends its craft pair."""
    if programme.status != ProgrammeStatus.DRAFT:
        raise RubricError("roles can only be changed on a draft")

    seen: list[uuid.UUID] = []
    for role_id in role_ids:
        if role_id not in seen:
            seen.append(role_id)
    if not seen:
        raise RubricError("Pick at least one role.")

    for role_id in seen:
        if session.get(Role, role_id) is None:
            raise RubricError("Role not found.")
        if session.get(RoleTemplate, role_id) is None:
            raise RubricError("Role not found.")

    existing = list(
        session.scalars(
            select(ProgrammeRole).where(ProgrammeRole.programme_id == programme.id)
        )
    )
    for row in existing:
        session.delete(row)
    session.flush()
    for position, role_id in enumerate(seen):
        session.add(
            ProgrammeRole(programme_id=programme.id, role_id=role_id, position=position)
        )
    programme.role_id = seen[0]
    session.flush()


def display_slot(criterion: RubricCriterion, role_count: int) -> str:
    if criterion.family in UNIVERSAL_FAMILIES:
        return str(criterion.family)
    if role_count <= 1:
        return str(criterion.family)
    return f"{criterion.family}{chr(ord('a') + criterion.lane)}"


def compose_rubric(
    session: Session, programme: Programme, content_dir: Path | None = None
) -> list[RubricCriterion]:
    """Seed universal rows plus each role's slot 2 and slot 3.

    Existing rows keep their wording. Adding a role appends its pair; removing
    a role drops that pair. Family 1 and 4 are never dropped.
    """
    if programme.status in FROZEN_STATUSES:
        raise RubricError("cannot compose a rubric for a programme already judging")

    role_ids = programme_role_ids(session, programme)
    if not role_ids:
        raise RubricError("Pick at least one role.")

    existing = {
        (c.family, c.role_id): c
        for c in session.scalars(
            select(RubricCriterion).where(RubricCriterion.programme_id == programme.id)
        )
    }

    wanted: set[tuple[int, uuid.UUID | None]] = {(1, None), (4, None)}
    written: list[RubricCriterion] = []
    placeholder = 2000

    def upsert(
        family: int,
        role_id: uuid.UUID | None,
        lane: int,
        name: str,
        a5: str,
        a3: str,
        a1: str,
    ) -> RubricCriterion:
        nonlocal placeholder
        key = (family, role_id)
        wanted.add(key)
        criterion = existing.get(key)
        if criterion is None:
            placeholder += 1
            criterion = RubricCriterion(
                programme_id=programme.id,
                family=family,
                role_id=role_id,
                lane=lane,
                slot=placeholder,
                name=name,
                anchor_5=a5,
                anchor_3=a3,
                anchor_1=a1,
            )
            session.add(criterion)
        else:
            criterion.family = family
            criterion.role_id = role_id
            criterion.lane = lane
            if not criterion.name:
                criterion.name = name
            if not criterion.anchor_5:
                criterion.anchor_5 = a5
            if not criterion.anchor_3:
                criterion.anchor_3 = a3
            if not criterion.anchor_1:
                criterion.anchor_1 = a1
        written.append(criterion)
        return criterion

    universal = {c.slot: c for c in universal_criteria(content_dir)}
    upsert(
        1,
        None,
        0,
        universal[1].name,
        universal[1].anchor_5,
        universal[1].anchor_3,
        universal[1].anchor_1,
    )
    for lane, role_id in enumerate(role_ids):
        template = session.get(RoleTemplate, role_id)
        if template is None:
            raise RubricError(
                f"role {role_id} has no template; run projet-seed before creating programmes"
            )
        upsert(
            2,
            role_id,
            lane,
            template.rubric_slot2_name,
            template.rubric_slot2_anchor_5,
            template.rubric_slot2_anchor_3,
            template.rubric_slot2_anchor_1,
        )
    for lane, role_id in enumerate(role_ids):
        template = session.get(RoleTemplate, role_id)
        if template is None:
            continue
        upsert(
            3,
            role_id,
            lane,
            template.rubric_slot3_name,
            template.rubric_slot3_anchor_5,
            template.rubric_slot3_anchor_3,
            template.rubric_slot3_anchor_1,
        )
    upsert(
        4,
        None,
        0,
        universal[4].name,
        universal[4].anchor_5,
        universal[4].anchor_3,
        universal[4].anchor_1,
    )

    for key, criterion in existing.items():
        if key not in wanted:
            session.delete(criterion)

    session.flush()
    ordered = sorted(
        [c for c in written if (c.family, c.role_id) in wanted],
        key=lambda c: (c.family, c.lane),
    )
    for index, criterion in enumerate(ordered, start=1):
        criterion.slot = 1000 + index
    session.flush()
    for index, criterion in enumerate(ordered, start=1):
        criterion.slot = index
    session.flush()
    return ordered


def edit_criterion(
    session: Session,
    criterion: RubricCriterion,
    *,
    name: str | None = None,
    anchor_5: str | None = None,
    anchor_3: str | None = None,
    anchor_1: str | None = None,
) -> RubricCriterion:
    """FR-072/FR-074/FR-076.

    Anchors on any family may be edited. Families 1 and 4 may not be renamed.
    """
    programme = session.get(Programme, criterion.programme_id)
    if programme is not None and programme.status in FROZEN_STATUSES:
        raise RubricError(
            "criteria are immutable once judging has started; editing now would "
            "invalidate scores already entered"
        )
    if name is not None and name != criterion.name and criterion.family in UNIVERSAL_FAMILIES:
        raise RubricError(
            f"slot {display_slot(criterion, 1)} is a universal criterion and cannot be renamed; "
            "its anchors can be edited"
        )
    if name is not None:
        criterion.name = name
    if anchor_5 is not None:
        criterion.anchor_5 = anchor_5
    if anchor_3 is not None:
        criterion.anchor_3 = anchor_3
    if anchor_1 is not None:
        criterion.anchor_1 = anchor_1
    session.flush()
    return criterion


def validate_for_publication(session: Session, programme: Programme) -> list[str]:
    """A programme cannot go draft -> open with an incomplete rubric."""
    criteria = list(
        session.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.programme_id == programme.id)
            .order_by(RubricCriterion.slot)
        )
    )
    role_count = len(programme_role_ids(session, programme))
    problems: list[str] = []
    families = {c.family for c in criteria}
    if 1 not in families:
        problems.append("slot 1 is missing")
    if 4 not in families:
        problems.append("slot 4 is missing")
    if 2 not in families:
        problems.append("slot 2 is missing")
    if 3 not in families:
        problems.append("slot 3 is missing")
    for criterion in criteria:
        if criterion.is_complete:
            continue
        missing = [
            label
            for label, value in (
                ("name", criterion.name),
                ("anchor 5", criterion.anchor_5),
                ("anchor 3", criterion.anchor_3),
                ("anchor 1", criterion.anchor_1),
            )
            if not value
        ]
        label = criterion.name or "unnamed"
        problems.append(
            f"slot {display_slot(criterion, role_count)} ({label}) missing: {', '.join(missing)}"
        )
    return problems


def publish(session: Session, programme: Programme) -> Programme:
    problems = validate_for_publication(session, programme)
    if problems:
        raise RubricError("cannot publish with an incomplete rubric:\n  " + "\n  ".join(problems))
    programme.status = ProgrammeStatus.OPEN
    session.flush()
    return programme
