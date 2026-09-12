"""Rubric composition and the invariants that keep scores comparable (FR-070).

Criteria are data, not code. This module is the only place that writes
RubricCriterion rows, because the rules about which slots may change and when
are not expressible as database constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import Programme, Role, RoleTemplate, RubricCriterion
from projet.models.enums import ProgrammeStatus
from projet.seeds.parsers import parse_universal_rubric

UNIVERSAL_SLOTS = (1, 4)
ROLE_SLOTS = (2, 3)
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
    """Slots 1 and 4, read from the same rubrics.md the roles come from."""
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


def compose_rubric(
    session: Session, programme: Programme, content_dir: Path | None = None
) -> list[RubricCriterion]:
    """Seed all four criteria for a new programme.

    Slots 1 and 4 come from the universal pair; slots 2 and 3 are pre-filled from
    the role template and admin edits them freely (FR-055, FR-073).
    """
    if programme.status in FROZEN_STATUSES:
        raise RubricError("cannot compose a rubric for a programme already judging")

    # Query rather than reading programme.criteria: the relationship can be
    # stale after an earlier compose in the same session, and a stale read here
    # inserts a duplicate slot instead of updating it.
    existing = {
        c.slot: c
        for c in session.scalars(
            select(RubricCriterion).where(RubricCriterion.programme_id == programme.id)
        )
    }
    role = session.get(Role, programme.role_id)
    template = session.get(RoleTemplate, programme.role_id) if role else None
    if template is None:
        raise RubricError(
            f"role {programme.role_id} has no template; run projet-seed before creating programmes"
        )

    written: list[RubricCriterion] = []
    for universal in universal_criteria(content_dir):
        criterion = existing.get(universal.slot) or RubricCriterion(
            programme_id=programme.id, slot=universal.slot
        )
        criterion.name = universal.name
        criterion.anchor_5 = universal.anchor_5
        criterion.anchor_3 = universal.anchor_3
        criterion.anchor_1 = universal.anchor_1
        session.add(criterion)
        written.append(criterion)

    role_slots = {
        2: (
            template.rubric_slot2_name,
            template.rubric_slot2_anchor_5,
            template.rubric_slot2_anchor_3,
            template.rubric_slot2_anchor_1,
        ),
        3: (
            template.rubric_slot3_name,
            template.rubric_slot3_anchor_5,
            template.rubric_slot3_anchor_3,
            template.rubric_slot3_anchor_1,
        ),
    }
    for slot, (name, a5, a3, a1) in role_slots.items():
        criterion = existing.get(slot) or RubricCriterion(programme_id=programme.id, slot=slot)
        criterion.name = name
        criterion.anchor_5 = a5
        criterion.anchor_3 = a3
        criterion.anchor_1 = a1
        session.add(criterion)
        written.append(criterion)

    session.flush()
    return sorted(written, key=lambda c: c.slot)


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

    Anchors on any slot may be edited — including a host's own phrasing on the 5.
    Slots 1 and 4 may not be renamed: holding that pair constant is what lets a
    Finance cohort be compared to an ESG cohort, and without it every cohort is
    an island.
    """
    programme = session.get(Programme, criterion.programme_id)
    if programme is not None and programme.status in FROZEN_STATUSES:
        raise RubricError(
            "criteria are immutable once judging has started; editing now would "
            "invalidate scores already entered"
        )
    if name is not None and name != criterion.name and criterion.slot in UNIVERSAL_SLOTS:
        raise RubricError(
            f"slot {criterion.slot} is a universal criterion and cannot be renamed; "
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
    """FR-075 — a programme cannot go draft -> open with an incomplete rubric."""
    criteria = list(
        session.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.programme_id == programme.id)
            .order_by(RubricCriterion.slot)
        )
    )
    problems: list[str] = []
    by_slot = {c.slot: c for c in criteria}
    for slot in (1, 2, 3, 4):
        criterion = by_slot.get(slot)
        if criterion is None:
            problems.append(f"slot {slot} is missing")
        elif not criterion.is_complete:
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
            problems.append(f"slot {slot} ({label}) missing: {', '.join(missing)}")
    return problems


def publish(session: Session, programme: Programme) -> Programme:
    problems = validate_for_publication(session, programme)
    if problems:
        raise RubricError("cannot publish with an incomplete rubric:\n  " + "\n  ".join(problems))
    programme.status = ProgrammeStatus.OPEN
    session.flush()
    return programme
