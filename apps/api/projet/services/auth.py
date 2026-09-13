"""Password authentication, one-time account tokens, and sessions.

Every actor type — platform staff, company users, participants — holds its own
email and password. Nothing about daily sign-in depends on inbox access.

The one thing an inbox is still needed for is the two moments a live session
cannot cover by definition: setting a password on a freshly invited account
(the person has no credential yet), and resetting a forgotten one. Those go
through `AccountActionToken`, which is single-purpose and single-use — proof
an address was reachable once, not an ongoing substitute for a password.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.config import get_settings
from projet.models import AccountActionToken, AuthSession, CompanyUser, Person, PlatformUser
from projet.models.base import utcnow
from projet.models.enums import AccountActionPurpose, ActorType, CompanyUserStatus
from projet.models.people import normalise_email

ACTION_TOKEN_TTL = timedelta(hours=48)
SESSION_TTL = timedelta(days=30)
SESSION_COOKIE = "projet_session"
TOKEN_BYTES = 32

# scrypt parameters. n=2^14 costs roughly 50-100ms per hash on ordinary
# hardware, which is the standard trade-off: slow enough to make guessing
# expensive, fast enough that a login does not feel slow.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


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


# -- passwords -----------------------------------------------------------------
#
# hashlib.scrypt is stdlib (no bcrypt/argon2 dependency to pull in) and is a
# memory-hard KDF, unlike a bare SHA-256 which a GPU makes cheap to brute-force.
# Stored as "scrypt$n$r$p$salt_hex$hash_hex" so parameters can change later
# without invalidating hashes already in the database.


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_DKLEN
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algorithm, n, r, p, salt_hex, hash_hex = stored.split("$")
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(hash_hex) // 2,
        )
        return hmac.compare_digest(derived.hex(), hash_hex)
    except (ValueError, IndexError):
        return False


PASSWORD_MIN_LENGTH = 8


def validate_password(password: str) -> str | None:
    """Return an error message, or None if the password is acceptable.

    Deliberately just a length floor. Composition rules (must contain a
    symbol, etc.) are well documented to push people toward predictable
    patterns and do not belong in something meant to be kept simple.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    return None


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


def authenticate_admin_code(session: Session, code: str) -> uuid.UUID | None:
    """A shared secret that signs straight in as platform admin, no password.

    Disabled unless PROJET_ADMIN_ACCESS_CODE is set — no fallback default, so
    an unconfigured deploy exposes nothing. Comparison is constant-time; the
    code is a password in every way that matters and should be treated like
    one — everyone who holds it has full admin access, with no per-person
    identity and no audit trail. Strictly weaker than the per-account password
    auth every other path here uses; it exists as a deliberate convenience
    trade-off, not a security feature.

    The admin user is bootstrapped on first use rather than requiring a
    platform_user row to pre-exist, since the whole point is not depending on
    anything else being set up first.
    """
    settings = get_settings()
    configured = settings.admin_access_code
    if not configured or not hmac.compare_digest(configured, code):
        return None

    email = normalise_email(settings.admin_bootstrap_email) or settings.admin_bootstrap_email
    user = session.scalar(select(PlatformUser).where(PlatformUser.email == email))
    if user is None:
        user = PlatformUser(name=settings.admin_bootstrap_name, email=email)
        session.add(user)
        session.flush()
    elif not user.is_active:
        return None
    return user.id


def resolve_actor_of_type(session: Session, email: str, actor_type: ActorType) -> uuid.UUID | None:
    """The same lookup as resolve_actor_by_email, but scoped to one portal.

    Each sign-in surface is for one actor type — a company login must not
    silently authenticate a participant who happens to share that email
    address, or the three portals are not actually separate, just three doors
    into the same ambiguous lookup.
    """
    normalised = normalise_email(email)
    if not normalised:
        return None

    if actor_type == ActorType.PLATFORM:
        platform = session.scalar(
            select(PlatformUser).where(PlatformUser.email == normalised, PlatformUser.is_active)
        )
        return platform.id if platform is not None else None

    if actor_type == ActorType.COMPANY_USER:
        company_user = session.scalar(
            select(CompanyUser)
            .where(CompanyUser.email == normalised)
            .where(CompanyUser.status != CompanyUserStatus.DISABLED)
        )
        return company_user.id if company_user is not None else None

    from sqlalchemy import func, or_

    person = session.scalar(
        select(Person).where(
            or_(
                func.lower(Person.contact_email) == normalised,
                func.lower(Person.google_email) == normalised,
            )
        )
    )
    return person.id if person is not None else None


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


def _password_hash_column(actor_type: ActorType, session: Session, subject_id: uuid.UUID):
    if actor_type == ActorType.PLATFORM:
        return session.get(PlatformUser, subject_id)
    if actor_type == ActorType.COMPANY_USER:
        return session.get(CompanyUser, subject_id)
    return session.get(Person, subject_id)


def authenticate(
    session: Session, *, email: str, password: str, actor_type: ActorType
) -> uuid.UUID | None:
    """Email and password, scoped to one actor type.

    actor_type is required, not inferred: the sign-in page you are on says
    which portal you mean, and authentication has to honour that rather than
    falling back to some priority order across account tables. Deliberately
    does the same amount of work (a lookup and a hash comparison) whether or
    not the address exists for that type, so response timing cannot be used
    to enumerate accounts.
    """
    subject_id = resolve_actor_of_type(session, email, actor_type)
    dummy_hash = (
        "scrypt$16384$8$1$00000000000000000000000000000000$"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    if subject_id is None:
        verify_password(password, dummy_hash)
        return None

    record = _password_hash_column(actor_type, session, subject_id)
    stored = getattr(record, "password_hash", None) if record is not None else None
    if not verify_password(password, stored):
        return None
    return subject_id


def set_password(
    session: Session, actor_type: ActorType, subject_id: uuid.UUID, password: str
) -> None:
    record = _password_hash_column(actor_type, session, subject_id)
    if record is None:
        raise AuthError("That account no longer exists.")
    record.password_hash = hash_password(password)
    session.flush()


# -- one-time account tokens: setup and reset only, never login --------------


def issue_account_action_token(
    session: Session,
    *,
    actor_type: ActorType,
    subject_id: uuid.UUID,
    email: str,
    purpose: AccountActionPurpose,
    redirect_path: str | None = None,
) -> tuple[AccountActionToken, str]:
    raw, hashed = _new_token()
    token = AccountActionToken(
        actor_type=actor_type,
        subject_id=subject_id,
        purpose=purpose,
        email=normalise_email(email) or email,
        token_hash=hashed,
        redirect_path=redirect_path,
        expires_at=utcnow() + ACTION_TOKEN_TTL,
    )
    session.add(token)
    session.flush()
    return token, raw


def issue_password_reset(
    session: Session, *, email: str, actor_type: ActorType
) -> tuple[AccountActionToken, str] | None:
    """Returns None for an unknown address in that portal; the caller must not
    reveal which — a different response enumerates who has an account."""
    subject_id = resolve_actor_of_type(session, email, actor_type)
    if subject_id is None:
        return None
    return issue_account_action_token(
        session,
        actor_type=actor_type,
        subject_id=subject_id,
        email=email,
        purpose=AccountActionPurpose.RESET_PASSWORD,
    )


def account_action_url(token: AccountActionToken, raw_token: str) -> str:
    path = (
        "/set-password" if token.purpose == AccountActionPurpose.SET_PASSWORD else "/reset-password"
    )
    params = {"token": raw_token}
    if token.redirect_path:
        params["next"] = token.redirect_path
    return f"{get_settings().app_base_url}{path}?{urlencode(params)}"


def consume_account_action_token(
    session: Session, raw_token: str, *, expected_purpose: AccountActionPurpose | None = None
) -> AccountActionToken:
    """Single-use: a link that has been clicked cannot be clicked again.

    Email clients and security scanners prefetch links, so this is not
    theoretical - a replayable token would let a scanner set someone's password.
    """
    token = session.scalar(
        select(AccountActionToken).where(AccountActionToken.token_hash == hash_token(raw_token))
    )
    if token is None:
        raise AuthError("That link is not valid.")
    if expected_purpose is not None and token.purpose != expected_purpose:
        raise AuthError("That link is not valid.")
    if token.consumed_at is not None:
        raise AuthError("That link has already been used. Request a new one.")
    if token.expires_at <= utcnow():
        raise AuthError("That link has expired. Request a new one.")

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
