"""Request-scoped identity and permission dependencies.

FR-015 scopes a rep to the programmes they are assigned to. A rep on the
sustainability challenge cannot see the data challenge's candidates — which
matters for enterprise later, where different functions run different challenges,
and costs nothing to build now.

Every permission check lives here rather than inside route bodies, so a route
that forgets one fails closed: it has no actor at all.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import false, select
from sqlalchemy.orm import Session

from projet.db import get_session
from projet.models import Programme, ProgrammeAssignment
from projet.models.enums import CompanyUserRole
from projet.services.auth import SESSION_COOKIE, Actor, resolve_session

# Roles that may configure programmes and see every programme in their company.
COMPANY_MANAGERS = (CompanyUserRole.OWNER, CompanyUserRole.ADMIN)


def current_actor(
    projet_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_session),
) -> Actor | None:
    return resolve_session(db, projet_session)


def require_actor(actor: Actor | None = Depends(current_actor)) -> Actor:
    if actor is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    return actor


def require_platform(actor: Actor = Depends(require_actor)) -> Actor:
    if not actor.is_platform:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required.")
    return actor


def require_company_user(actor: Actor = Depends(require_actor)) -> Actor:
    if not actor.is_company_user:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Company access required.")
    return actor


def require_participant(actor: Actor = Depends(require_actor)) -> Actor:
    if not actor.is_participant:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Participant access required.")
    return actor


def require_company_role(*roles: CompanyUserRole) -> Callable[..., Actor]:
    """Company users with one of these roles. Platform staff always pass."""

    def dependency(actor: Actor = Depends(require_actor)) -> Actor:
        if actor.is_platform:
            return actor
        if not actor.is_company_user or actor.role not in {r.value for r in roles}:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Your account does not have permission to do that.",
            )
        return actor

    return dependency


require_company_manager = require_company_role(*COMPANY_MANAGERS)


def can_see_programme(db: Session, actor: Actor, programme: Programme) -> bool:
    """FR-015 — the single answer to 'is this programme yours?'.

    Platform staff see everything. An owner or admin sees their whole company.
    A rep or viewer sees only what they are assigned to.
    """
    if actor.is_platform:
        return True
    if not actor.is_company_user or programme.company_id != actor.company_id:
        return False
    if actor.role in {r.value for r in COMPANY_MANAGERS}:
        return True
    assignment = db.scalar(
        select(ProgrammeAssignment)
        .where(ProgrammeAssignment.programme_id == programme.id)
        .where(ProgrammeAssignment.company_user_id == actor.id)
    )
    return assignment is not None


def can_score_programme(db: Session, actor: Actor, programme: Programme) -> bool:
    if actor.is_platform:
        return True
    if not can_see_programme(db, actor, programme):
        return False
    if actor.role in {r.value for r in COMPANY_MANAGERS}:
        return True
    assignment = db.scalar(
        select(ProgrammeAssignment)
        .where(ProgrammeAssignment.programme_id == programme.id)
        .where(ProgrammeAssignment.company_user_id == actor.id)
    )
    return bool(assignment and assignment.can_score)


def visible_programmes(db: Session, actor: Actor):
    """The programme list this actor is allowed to see, as a select()."""
    statement = select(Programme)
    if actor.is_platform:
        return statement
    if not actor.is_company_user:
        # Participants reach programmes through their participation, not here.
        return statement.where(false())
    statement = statement.where(Programme.company_id == actor.company_id)
    if actor.role in {r.value for r in COMPANY_MANAGERS}:
        return statement
    return statement.join(
        ProgrammeAssignment, ProgrammeAssignment.programme_id == Programme.id
    ).where(ProgrammeAssignment.company_user_id == actor.id)


def get_programme_or_404(
    programme_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> Programme:
    """404 rather than 403 for a programme the actor cannot see.

    Telling a rep that a programme exists but is not theirs leaks the other
    function's activity, which is exactly what FR-015 is preventing.
    """
    programme = db.get(Programme, programme_id)
    if programme is None or not can_see_programme(db, actor, programme):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme not found.")
    return programme


def client_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")
