"""Sign in, sign out, password reset, and who am I.

Every actor type has its own email and password (FR-010, extended beyond the
original magic-link-only design for company users). The only email-dependent
moment is choosing a password in the first place — new account or reset — which
runs through the one-time AccountActionToken rather than through login itself.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from projet.api.deps import current_actor, require_actor
from projet.config import get_settings
from projet.db import get_session
from projet.models.enums import AccountActionPurpose, OutboxSubjectType
from projet.outbox.account_effects import PASSWORD_RESET_EMAIL
from projet.outbox.effects import enqueue
from projet.services.auth import (
    SESSION_COOKIE,
    SESSION_TTL,
    Actor,
    AuthError,
    account_action_url,
    authenticate,
    consume_account_action_token,
    end_session,
    issue_password_reset,
    load_actor,
    set_password,
    start_session,
    validate_password,
)
from projet.services.people import looks_like_email

router = APIRouter(prefix="/auth", tags=["auth"])


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
    """Only same-site paths. An absolute URL here would make an emailed link an
    open redirect, and it arrives somewhere easy to hand around."""
    if not path or not path.startswith("/") or path.startswith("//"):
        return None
    return path


def _set_session_cookie(response: Response, raw_session: str) -> None:
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


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        if not looks_like_email(value):
            raise ValueError("That does not look like an email address.")
        return value


@router.post("/login", response_model=ActorResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> ActorResponse:
    resolved = authenticate(db, email=payload.email, password=payload.password)
    if resolved is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That email or password is not right.")
    actor_type, subject_id = resolved

    _, raw_session = start_session(
        db,
        actor_type=actor_type,
        subject_id=subject_id,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    _set_session_cookie(response, raw_session)
    actor = load_actor(db, actor_type, subject_id)
    assert actor is not None
    return ActorResponse.of(actor)


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


class PasswordResetRequest(BaseModel):
    email: str = Field(max_length=320)


@router.post("/password/forgot")
def forgot_password(
    payload: PasswordResetRequest,
    db: Session = Depends(get_session),
) -> dict:
    """Deliberately the same response whether or not the address is known -
    a different one enumerates who has an account."""
    issued = issue_password_reset(db, email=payload.email)
    if issued is not None:
        token, raw = issued
        enqueue(
            db,
            subject_type=OutboxSubjectType.ACCOUNT_ACTION,
            subject_id=token.id,
            effect_type=PASSWORD_RESET_EMAIL,
            payload={"url": account_action_url(token, raw)},
        )
    db.commit()
    return {
        "sent": True,
        "message": "If that address has an account, a password reset link is on its way.",
    }


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=1, max_length=200)


@router.post("/password/reset", response_model=ActorResponse)
def reset_password(
    payload: PasswordResetConfirm,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> ActorResponse:
    error = validate_password(payload.password)
    if error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error)

    try:
        token = consume_account_action_token(
            db, payload.token, expected_purpose=AccountActionPurpose.RESET_PASSWORD
        )
    except AuthError as auth_error:
        db.commit()  # keep the consumed-at write on a replayed token
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(auth_error)) from auth_error

    set_password(db, token.actor_type, token.subject_id, payload.password)
    _, raw_session = start_session(
        db,
        actor_type=token.actor_type,
        subject_id=token.subject_id,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    _set_session_cookie(response, raw_session)
    actor = load_actor(db, token.actor_type, token.subject_id)
    assert actor is not None
    return ActorResponse.of(actor)


class SetPasswordConfirm(BaseModel):
    """Same shape as a reset, different purpose: a freshly invited account
    choosing its first password rather than replacing one."""

    token: str
    password: str = Field(min_length=1, max_length=200)


@router.post("/password/set", response_model=ActorResponse)
def set_initial_password(
    payload: SetPasswordConfirm,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> ActorResponse:
    error = validate_password(payload.password)
    if error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error)

    try:
        token = consume_account_action_token(
            db, payload.token, expected_purpose=AccountActionPurpose.SET_PASSWORD
        )
    except AuthError as auth_error:
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(auth_error)) from auth_error

    set_password(db, token.actor_type, token.subject_id, payload.password)
    _, raw_session = start_session(
        db,
        actor_type=token.actor_type,
        subject_id=token.subject_id,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    _set_session_cookie(response, raw_session)
    actor = load_actor(db, token.actor_type, token.subject_id)
    assert actor is not None
    return ActorResponse.of(actor)


@router.get("/me", response_model=ActorResponse)
def me(actor: Actor = Depends(require_actor)) -> ActorResponse:
    return ActorResponse.of(actor)


@router.get("/session", response_model=ActorResponse | None)
def session_probe(actor: Actor | None = Depends(current_actor)) -> ActorResponse | None:
    """Unauthenticated probe, so the frontend can render signed-out state
    without a 401 in the console on every page load."""
    return ActorResponse.of(actor) if actor else None
