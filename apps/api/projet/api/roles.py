"""The role taxonomy, as the company picks from it (FR-040, FR-051-053)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import require_actor
from projet.api.schemas import RoleImplications, RoleSummary
from projet.db import get_session
from projet.models import Role, RoleTemplate
from projet.services.auth import Actor

router = APIRouter(prefix="/roles", tags=["roles"])


class ClusterOut(BaseModel):
    """FR-052 — cluster first, then role.

    A flat list of 75 is unusable; picking "Finance" then "Venture Capital" is
    two taps and prevents mis-tagging.
    """

    cluster: str
    roles: list[RoleSummary]


@router.get("/clusters", response_model=list[ClusterOut])
def list_clusters(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> list[ClusterOut]:
    roles = list(db.scalars(select(Role).where(Role.is_active).order_by(Role.sort_order)))
    grouped: dict[str, list[RoleSummary]] = {}
    for role in roles:
        grouped.setdefault(role.cluster, []).append(RoleSummary.model_validate(role))
    return [ClusterOut(cluster=name, roles=items) for name, items in grouped.items()]


@router.get("/search", response_model=list[RoleSummary])
def search_roles(
    q: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> list[RoleSummary]:
    """FR-043 — search runs across names and aliases, so "data analyst" or "BI"
    lands on Data Analytics rather than creating a near-duplicate."""
    needle = q.strip().lower()
    matches = []
    for role in db.scalars(select(Role).where(Role.is_active).order_by(Role.sort_order)):
        haystack = [role.name.lower(), role.cluster.lower()]
        haystack.extend(alias.lower() for alias in role.aliases or [])
        if any(needle in entry for entry in haystack):
            matches.append(RoleSummary.model_validate(role))
    return matches


@router.get("/{role_id}/implications", response_model=RoleImplications)
def role_implications(
    role_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> RoleImplications:
    """FR-053 — what picking this role commits them to, before they commit.

    The deliverable, the sources, the two role-specific criteria and the
    low-friction asks. Seeing the artifact spec now is what prevents discovering
    after the cohort ran that it was not what they wanted.
    """
    role = db.get(Role, role_id)
    template = db.get(RoleTemplate, role_id) if role else None
    if role is None or template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found.")

    from projet.services.rubric import universal_criteria

    universal = {c.slot: c for c in universal_criteria()}
    # Built in slot order rather than sorted: the order is fixed by the rubric
    # design, with the two universal criteria bracketing the two role-specific
    # ones (FR-071).
    criteria: list[dict] = [
        {
            "slot": 1,
            "name": universal[1].name,
            "anchor_5": universal[1].anchor_5,
            "universal": True,
        },
        {
            "slot": 2,
            "name": template.rubric_slot2_name,
            "anchor_5": template.rubric_slot2_anchor_5,
            "universal": False,
        },
        {
            "slot": 3,
            "name": template.rubric_slot3_name,
            "anchor_5": template.rubric_slot3_anchor_5,
            "universal": False,
        },
        {
            "slot": 4,
            "name": universal[4].name,
            "anchor_5": universal[4].anchor_5,
            "universal": True,
        },
    ]

    return RoleImplications(
        role=RoleSummary.model_validate(role),
        default_deliverable=template.default_deliverable,
        public_sources=[s.get("label", "") for s in template.public_sources or []],
        student_tools=template.student_tools or [],
        judging_criteria=criteria,
        company_asks_easy=template.asks_easy or [],
        delivery_risk_note=template.delivery_risk_note,
    )
