"""Magic-link issuing, consumption and session management (FR-010).

The whole flow is: request a link, click it, you are signed in and on the page
you were going to. Authentication must never stand between a rep and the thing
they came to do.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.config import get_settings
from projet.models import AuthSession, CompanyUser, MagicLinkToken, Person, PlatformUser
from projet.models.base import utcnow
from projet.models.enums import ActorType, CompanyUserStatus
from projet.models.people import normalise_email

MAGIC_LINK_TTL = timedelta(minutes=20)
SESSION_TTL = timedelta(days=30)
SESSION_COOKIE = "projet_session"
TOKEN_BYTES = 32


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class Actor:
    """Who is making a request. Resolved once per request by the dependency."""

    actor_type: ActorType
    id: uuid.UUID
    email: str
    name: str
    company_id: uuid.UUID | None = None
    role: str | None = None

    @property
    def is_platform(self) -> bool:
        return self.actor_type == ActorType.PLATFORM

    @property
    def is_company_user(self) -> bool:
        return self.actor_type == ActorType.COMPANY_USER

    @property
    def is_participant(self) -> bool:
        return self.actor_type == ActorType.PARTICIPANT


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, hash_token(raw)


# -- resolving an email to an actor -------------------------------------------


def resolve_actor_by_email(session: Session, email: str) -> tuple[ActorType, uuid.UUID] | None:
    """Find who this address belongs to.

    Checked in order of authority. An address that is both a company user and a
    participant resolves to the company user, because that is the account with
    access to other people's data and the more conservative answer if we are
    wrong.
    """
    normalised = normalise_email(email)
    if not normalised:
        return None

    platform = session.scalar(
        select(PlatformUser).where(PlatformUser.email == normalised, PlatformUser.is_active)
    )
    if platform is not None:
        return ActorType.PLATFORM, platform.id

    company_user = session.scalar(
        select(CompanyUser)
        .where(CompanyUser.email == normalised)
        .where(CompanyUser.status != CompanyUserStatus.DISABLED)
    )
    if company_user is not None:
        return ActorType.COMPANY_USER, company_user.id

    from sqlalchemy import func, or_

    person = session.scalar(
        select(Person).where(
            or_(
                func.lower(Person.contact_email) == normalised,
                func.lower(Person.google_email) == normalised,
            )
        )
    )
    if person is not None:
        return ActorType.PARTICIPANT, person.id
    return None


def load_actor(session: Session, actor_type: ActorType, subject_id: uuid.UUID) -> Actor | None:
    if actor_type == ActorType.PLATFORM:
        platform_user = session.get(PlatformUser, subject_id)
        if platform_user is None or not platform_user.is_active:
            return None
        return Actor(
            actor_type,
            platform_user.id,
            platform_user.email,
            platform_user.name,
            role=platform_user.role.value,
        )

    if actor_type == ActorType.COMPANY_USER:
        company_user = session.get(CompanyUser, subject_id)
        if company_user is None or company_user.status == CompanyUserStatus.DISABLED:
            return None
        return Actor(
            actor_type,
            company_user.id,
            company_user.email,
            company_user.name,
            company_id=company_user.company_id,
            role=company_user.role.value,
        )

    person = session.get(Person, subject_id)
    if person is None:
        return None
    return Actor(actor_type, person.id, person.contact_email, person.name)


# -- magic links --------------------------------------------------------------


def issue_magic_link(
    session: Session,
    *,
    email: str,
    redirect_path: str | None = None,
) -> tuple[MagicLinkToken, str] | None:
    """Create a single-use token. Returns None when the address is unknown.

    The caller must not reveal which it was: telling an anonymous requester
    whether an address has an account enumerates the candidate pool.
    """
    resolved = resolve_actor_by_email(session, email)
    if resolved is None:
        return None
    actor_type, subject_id = resolved

    raw, hashed = _new_token()
    token = MagicLinkToken(
        actor_type=actor_type,
        subject_id=subject_id,
        email=normalise_email(email) or email,
        token_hash=hashed,
        redirect_path=redirect_path,
        expires_at=utcnow() + MAGIC_LINK_TTL,
    )
    session.add(token)
    session.flush()
    return token, raw


def magic_link_url(raw_token: str, redirect_path: str | None = None) -> str:
    params = {"token": raw_token}
    if redirect_path:
        params["next"] = redirect_path
    return f"{get_settings().app_base_url}/auth/verify?{urlencode(params)}"


def consume_magic_link(session: Session, raw_token: str) -> MagicLinkToken:
    """Single-use: a token that has been clicked cannot be clicked again.

    Email clients and security scanners prefetch links, so this is not a
    theoretical concern — a replayed token is a second session for whoever has
    the email.
    """
    token = session.scalar(
        select(MagicLinkToken).where(MagicLinkToken.token_hash == hash_token(raw_token))
    )
    if token is None:
        raise AuthError("That sign-in link is not valid.")
    if token.consumed_at is not None:
        raise AuthError("That sign-in link has already been used. Request a new one.")
    if token.expires_at <= utcnow():
        raise AuthError("That sign-in link has expired. Request a new one.")

    token.consumed_at = utcnow()
    session.flush()
    return token


# -- sessions -----------------------------------------------------------------


def start_session(
    session: Session,
    *,
    actor_type: ActorType,
    subject_id: uuid.UUID,
    user_agent: str | None = None,
) -> tuple[AuthSession, str]:
    raw, hashed = _new_token()
    row = AuthSession(
        actor_type=actor_type,
        subject_id=subject_id,
        token_hash=hashed,
        user_agent=(user_agent or "")[:400] or None,
        expires_at=utcnow() + SESSION_TTL,
    )
    session.add(row)

    if actor_type == ActorType.PLATFORM:
        user = session.get(PlatformUser, subject_id)
        if user:
            user.last_login_at = utcnow()
    elif actor_type == ActorType.COMPANY_USER:
        company_user = session.get(CompanyUser, subject_id)
        if company_user:
            company_user.last_login_at = utcnow()
            # An invited user becomes active by signing in; there is no separate
            # accept-invitation step to forget about.
            if company_user.status == CompanyUserStatus.INVITED:
                company_user.status = CompanyUserStatus.ACTIVE

    session.flush()
    return row, raw


def resolve_session(session: Session, raw_token: str | None) -> Actor | None:
    if not raw_token:
        return None
    row = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if row is None or not row.is_live:
        return None

    actor = load_actor(session, row.actor_type, row.subject_id)
    if actor is None:
        return None

    # Cheap liveness signal without writing on every request.
    if (utcnow() - row.last_seen_at) > timedelta(hours=1):
        row.last_seen_at = utcnow()
    return actor


def end_session(session: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if row is not None and row.revoked_at is None:
        row.revoked_at = utcnow()
        session.flush()


def revoke_all_sessions(session: Session, actor_type: ActorType, subject_id: uuid.UUID) -> int:
    rows = list(
        session.scalars(
            select(AuthSession)
            .where(AuthSession.actor_type == actor_type)
            .where(AuthSession.subject_id == subject_id)
            .where(AuthSession.revoked_at.is_(None))
        )
    )
    for row in rows:
        row.revoked_at = utcnow()
    session.flush()
    return len(rows)
