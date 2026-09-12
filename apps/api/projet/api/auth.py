"""Sign in, sign out, and who am I.

Requesting a link and clicking it is the whole flow (FR-011).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from projet.api.deps import current_actor, require_actor
from projet.config import get_settings
from projet.db import get_session
from projet.models.enums import OutboxSubjectType
from projet.outbox.auth_effects import MAGIC_LINK_EMAIL
from projet.outbox.effects import enqueue
from projet.services.auth import (
    SESSION_COOKIE,
    SESSION_TTL,
    Actor,
    AuthError,
    consume_magic_link,
    end_session,
    issue_magic_link,
    load_actor,
    magic_link_url,
    start_session,
)
from projet.services.people import looks_like_email

router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkRequest(BaseModel):
    email: str = Field(max_length=320)
    next: str | None = Field(default=None, description="Path to land on after signing in")

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        if not looks_like_email(value):
            raise ValueError("That does not look like an email address.")
        return value


class MagicLinkResponse(BaseModel):
    sent: bool
    message: str


class ActorResponse(BaseModel):
    actor_type: str
    id: str
    email: str
    name: str
    company_id: str | None = None
    role: str | None = None

    @classmethod
    def of(cls, actor: Actor) -> ActorResponse:
        return cls(
            actor_type=actor.actor_type.value,
            id=str(actor.id),
            email=actor.email,
            name=actor.name,
            company_id=str(actor.company_id) if actor.company_id else None,
            role=actor.role,
        )


def _safe_redirect(path: str | None) -> str | None:
    """Only same-site paths. An absolute URL here would make the sign-in link an
    open redirect, and it arrives by email where it is easy to hand around."""
    if not path or not path.startswith("/") or path.startswith("//"):
        return None
    return path


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(
    payload: MagicLinkRequest,
    db: Session = Depends(get_session),
) -> MagicLinkResponse:
    issued = issue_magic_link(db, email=payload.email, redirect_path=_safe_redirect(payload.next))
    if issued is not None:
        token, raw = issued
        enqueue(
            db,
            subject_type=OutboxSubjectType.MAGIC_LINK,
            subject_id=token.id,
            effect_type=MAGIC_LINK_EMAIL,
            payload={"url": magic_link_url(raw, token.redirect_path)},
        )
    db.commit()

    # Deliberately identical whether or not the address is known: a different
    # answer here enumerates who has an account.
    return MagicLinkResponse(
        sent=True,
        message="If that address has an account, a sign-in link is on its way.",
    )


class VerifyRequest(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    actor: ActorResponse
    next: str | None = None


@router.post("/verify", response_model=VerifyResponse)
def verify_magic_link(
    payload: VerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> VerifyResponse:
    try:
        token = consume_magic_link(db, payload.token)
    except AuthError as error:
        db.commit()  # keep the consumed-at write on a replayed token
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    actor = load_actor(db, token.actor_type, token.subject_id)
    if actor is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That account is no longer active.")

    _, raw_session = start_session(
        db,
        actor_type=token.actor_type,
        subject_id=token.subject_id,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        raw_session,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        path="/",
    )
    return VerifyResponse(actor=ActorResponse.of(actor), next=token.redirect_path)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> dict:
    end_session(db, request.cookies.get(SESSION_COOKIE))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"signed_out": True}


@router.get("/me", response_model=ActorResponse)
def me(actor: Actor = Depends(require_actor)) -> ActorResponse:
    return ActorResponse.of(actor)


@router.get("/session", response_model=ActorResponse | None)
def session_probe(actor: Actor | None = Depends(current_actor)) -> ActorResponse | None:
    """Unauthenticated probe, so the frontend can render signed-out state
    without a 401 in the console on every page load."""
    return ActorResponse.of(actor) if actor else None
