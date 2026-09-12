"""Magic-link auth and permission scoping (FR-010).

Two things are load-bearing here and easy to get quietly wrong: a sign-in link
must work exactly once, and a rep must not be able to see another function's
candidates.
"""

from __future__ import annotations

import uuid

import pytest

from projet.models import CompanyUser, PlatformUser
from projet.models.base import utcnow
from projet.models.enums import ActorType, CompanyUserRole, CompanyUserStatus
from projet.services.auth import (
    AuthError,
    consume_magic_link,
    end_session,
    hash_token,
    issue_magic_link,
    resolve_actor_by_email,
    resolve_session,
    revoke_all_sessions,
    start_session,
)


@pytest.fixture
def platform_user(session) -> PlatformUser:
    user = PlatformUser(name="Andrei", email=f"admin-{uuid.uuid4().hex[:6]}@projet.sg")
    session.add(user)
    session.flush()
    return user


def test_a_link_is_issued_for_a_known_company_user(session, rep):
    issued = issue_magic_link(session, email=rep.email)
    assert issued is not None
    token, raw = issued

    assert token.actor_type == ActorType.COMPANY_USER
    assert token.subject_id == rep.id
    assert token.token_hash == hash_token(raw)
    assert token.token_hash != raw, "the raw token must never be stored"


def test_an_unknown_address_yields_nothing(session):
    assert issue_magic_link(session, email="nobody@nowhere.test") is None


def test_a_participant_gets_the_same_mechanism(session, participant_factory):
    """One auth flow for all three actor types."""
    participant = participant_factory()
    issued = issue_magic_link(session, email=participant.person.contact_email)

    assert issued is not None
    assert issued[0].actor_type == ActorType.PARTICIPANT


def test_a_company_user_outranks_a_participant_on_the_same_address(
    session, company, participant_factory
):
    """If one address is both, resolve to the account with access to other
    people's data — the conservative answer if we are wrong."""
    participant = participant_factory()
    shared = participant.person.contact_email
    session.add(
        CompanyUser(
            company_id=company.id,
            name="Dual",
            email=shared,
            role=CompanyUserRole.REP,
        )
    )
    session.flush()

    actor_type, _ = resolve_actor_by_email(session, shared)
    assert actor_type == ActorType.COMPANY_USER


def test_a_disabled_company_user_cannot_sign_in(session, rep):
    rep.status = CompanyUserStatus.DISABLED
    session.flush()
    assert issue_magic_link(session, email=rep.email) is None


def test_a_link_works_exactly_once(session, rep):
    _, raw = issue_magic_link(session, email=rep.email)
    consumed = consume_magic_link(session, raw)
    assert consumed.consumed_at is not None

    with pytest.raises(AuthError, match="already been used"):
        consume_magic_link(session, raw)


def test_an_expired_link_is_refused(session, rep):
    token, raw = issue_magic_link(session, email=rep.email)
    token.expires_at = utcnow()
    session.flush()

    with pytest.raises(AuthError, match="expired"):
        consume_magic_link(session, raw)


def test_a_forged_token_is_refused(session, rep):
    issue_magic_link(session, email=rep.email)
    with pytest.raises(AuthError, match="not valid"):
        consume_magic_link(session, "not-a-real-token")


def test_signing_in_activates_an_invited_user(session, rep):
    """There is no separate accept-invitation step to forget about."""
    rep.status = CompanyUserStatus.INVITED
    session.flush()

    start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)

    assert rep.status == CompanyUserStatus.ACTIVE
    assert rep.last_login_at is not None


def test_a_session_resolves_back_to_its_actor(session, rep):
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    actor = resolve_session(session, raw)

    assert actor is not None
    assert actor.id == rep.id
    assert actor.is_company_user
    assert actor.company_id == rep.company_id


def test_a_revoked_session_stops_resolving(session, rep):
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    end_session(session, raw)
    assert resolve_session(session, raw) is None


def test_revoking_all_sessions_signs_out_every_device(session, rep):
    _, first = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    _, second = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)

    assert revoke_all_sessions(session, ActorType.COMPANY_USER, rep.id) == 2
    assert resolve_session(session, first) is None
    assert resolve_session(session, second) is None


def test_an_expired_session_stops_resolving(session, rep):
    row, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    row.expires_at = utcnow()
    session.flush()
    assert resolve_session(session, raw) is None


def test_a_session_for_a_deleted_actor_resolves_to_nothing(session, rep):
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    session.delete(rep)
    session.flush()
    assert resolve_session(session, raw) is None


def test_platform_users_resolve_as_platform(session, platform_user):
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=platform_user.id)
    actor = resolve_session(session, raw)

    assert actor is not None and actor.is_platform
    assert not actor.is_company_user
