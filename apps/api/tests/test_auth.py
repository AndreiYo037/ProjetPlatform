"""Password auth, one-time account tokens and sessions.

Two properties are load-bearing and get their own tests: a stored password is
never recoverable from the database row, and an account-action token can be
used exactly once.
"""

from __future__ import annotations

import uuid

import pytest

from projet.models import PlatformUser
from projet.models.base import utcnow
from projet.models.enums import AccountActionPurpose, ActorType, CompanyUserStatus
from projet.services.auth import (
    AuthError,
    account_action_url,
    authenticate,
    consume_account_action_token,
    end_session,
    hash_password,
    issue_account_action_token,
    issue_password_reset,
    resolve_actor_by_email,
    resolve_session,
    revoke_all_sessions,
    set_password,
    start_session,
    validate_password,
    verify_password,
)


@pytest.fixture
def platform_user(session) -> PlatformUser:
    user = PlatformUser(name="Andrei", email=f"admin-{uuid.uuid4().hex[:6]}@projet.sg")
    session.add(user)
    session.flush()
    return user


# -- password hashing ---------------------------------------------------------


def test_a_hash_never_stores_the_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert "correct horse battery staple" not in hashed


def test_the_right_password_verifies():
    hashed = hash_password("hunter22")
    assert verify_password("hunter22", hashed)


def test_the_wrong_password_is_refused():
    hashed = hash_password("hunter22")
    assert not verify_password("hunter23", hashed)


def test_a_missing_hash_never_verifies():
    assert not verify_password("anything", None)


def test_a_malformed_hash_is_refused_not_raised():
    assert not verify_password("anything", "not-a-real-hash")


def test_two_hashes_of_the_same_password_differ():
    """Salted: identical passwords must not produce identical rows, or a
    database leak would reveal which two accounts share a password."""
    assert hash_password("hunter22") != hash_password("hunter22")


@pytest.mark.parametrize("password,ok", [("short", False), ("exactly8", True), ("a" * 40, True)])
def test_password_length_is_enforced(password, ok):
    assert (validate_password(password) is None) is ok


# -- authenticate --------------------------------------------------------------


def test_a_company_user_can_log_in_once_a_password_is_set(session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    resolved = authenticate(
        session, email=rep.email, password="hunter22", actor_type=ActorType.COMPANY_USER
    )

    assert resolved == rep.id


def test_the_wrong_password_does_not_authenticate(session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    assert (
        authenticate(session, email=rep.email, password="wrong", actor_type=ActorType.COMPANY_USER)
        is None
    )


def test_an_account_with_no_password_set_cannot_log_in(session, rep):
    """An invited user who has not yet chosen a password is not a login."""
    assert (
        authenticate(
            session, email=rep.email, password="anything", actor_type=ActorType.COMPANY_USER
        )
        is None
    )


def test_an_unknown_address_does_not_authenticate(session):
    assert (
        authenticate(
            session,
            email="nobody@nowhere.test",
            password="anything",
            actor_type=ActorType.COMPANY_USER,
        )
        is None
    )


def test_a_disabled_company_user_cannot_log_in(session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    rep.status = CompanyUserStatus.DISABLED
    session.flush()
    assert (
        authenticate(
            session, email=rep.email, password="hunter22", actor_type=ActorType.COMPANY_USER
        )
        is None
    )


def test_a_participant_authenticates_the_same_way(session, participant_factory):
    participant = participant_factory()
    set_password(session, ActorType.PARTICIPANT, participant.person_id, "hunter22")

    resolved = authenticate(
        session,
        email=participant.person.contact_email,
        password="hunter22",
        actor_type=ActorType.PARTICIPANT,
    )
    assert resolved == participant.person_id


def test_platform_users_authenticate_the_same_way(session, platform_user):
    set_password(session, ActorType.PLATFORM, platform_user.id, "hunter22")
    resolved = authenticate(
        session, email=platform_user.email, password="hunter22", actor_type=ActorType.PLATFORM
    )
    assert resolved == platform_user.id


def test_a_company_login_does_not_authenticate_a_participant_with_the_same_email(
    session, company, participant_factory
):
    """The whole point of scoping by actor_type: a shared email must not let a
    participant sign in through the company portal, or vice versa."""
    participant = participant_factory()
    set_password(session, ActorType.PARTICIPANT, participant.person_id, "hunter22")

    resolved = authenticate(
        session,
        email=participant.person.contact_email,
        password="hunter22",
        actor_type=ActorType.COMPANY_USER,
    )
    assert resolved is None


def test_a_company_user_outranks_a_participant_on_the_same_address(
    session, company, participant_factory
):
    from projet.models import CompanyUser
    from projet.models.enums import CompanyUserRole

    participant = participant_factory()
    shared = participant.person.contact_email
    session.add(
        CompanyUser(company_id=company.id, name="Dual", email=shared, role=CompanyUserRole.REP)
    )
    session.flush()

    actor_type, _ = resolve_actor_by_email(session, shared)
    assert actor_type == ActorType.COMPANY_USER


# -- account action tokens ------------------------------------------------------


def test_password_reset_is_scoped_to_the_requested_actor_type(
    session, company, participant_factory
):
    from projet.services.auth import issue_password_reset

    participant = participant_factory()
    shared = participant.person.contact_email
    from projet.models import CompanyUser
    from projet.models.enums import CompanyUserRole

    session.add(
        CompanyUser(company_id=company.id, name="Dual", email=shared, role=CompanyUserRole.REP)
    )
    session.flush()

    for_company = issue_password_reset(session, email=shared, actor_type=ActorType.COMPANY_USER)
    for_participant = issue_password_reset(session, email=shared, actor_type=ActorType.PARTICIPANT)

    assert for_company is not None and for_company[0].actor_type == ActorType.COMPANY_USER
    assert for_participant is not None and for_participant[0].actor_type == ActorType.PARTICIPANT
    assert for_company[0].subject_id != for_participant[0].subject_id


def test_a_set_password_token_can_only_set_a_password_once(session, rep):
    token, raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
    )
    consumed = consume_account_action_token(
        session, raw, expected_purpose=AccountActionPurpose.SET_PASSWORD
    )
    assert consumed.id == token.id

    with pytest.raises(AuthError, match="already been used"):
        consume_account_action_token(session, raw)


def test_an_expired_token_is_refused(session, rep):
    token, raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
    )
    token.expires_at = utcnow()
    session.flush()

    with pytest.raises(AuthError, match="expired"):
        consume_account_action_token(session, raw)


def test_a_forged_token_is_refused(session, rep):
    issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
    )
    with pytest.raises(AuthError, match="not valid"):
        consume_account_action_token(session, "not-a-real-token")


def test_a_reset_token_cannot_be_used_where_a_set_password_token_is_expected(session, rep):
    """The two purposes must not be interchangeable, or a reset link could be
    replayed to hijack an invited account that never set a password."""
    _, raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.RESET_PASSWORD,
    )
    with pytest.raises(AuthError, match="not valid"):
        consume_account_action_token(
            session, raw, expected_purpose=AccountActionPurpose.SET_PASSWORD
        )


def test_password_reset_is_issued_for_a_known_address(session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    issued = issue_password_reset(session, email=rep.email, actor_type=ActorType.COMPANY_USER)

    assert issued is not None
    token, _ = issued
    assert token.purpose == AccountActionPurpose.RESET_PASSWORD


def test_password_reset_is_silent_for_an_unknown_address(session):
    assert (
        issue_password_reset(
            session, email="nobody@nowhere.test", actor_type=ActorType.COMPANY_USER
        )
        is None
    )


def test_the_account_action_url_routes_by_purpose(session, rep):
    set_token, set_raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.SET_PASSWORD,
    )
    reset_token, reset_raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.RESET_PASSWORD,
    )
    assert "/set-password" in account_action_url(set_token, set_raw)
    assert "/reset-password" in account_action_url(reset_token, reset_raw)


def test_resetting_a_password_replaces_the_old_one(session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter23")

    assert (
        authenticate(
            session, email=rep.email, password="hunter22", actor_type=ActorType.COMPANY_USER
        )
        is None
    )
    assert (
        authenticate(
            session, email=rep.email, password="hunter23", actor_type=ActorType.COMPANY_USER
        )
        is not None
    )


# -- sessions -----------------------------------------------------------------


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


# -- admin access code (dev/demo shortcut, not a hardened login) -----------


def test_the_admin_code_is_disabled_unless_configured(session, monkeypatch):
    """No fallback default: unset means off, not 'guessable'."""
    from projet.config import get_settings
    from projet.services.auth import authenticate_admin_code

    get_settings.cache_clear()
    monkeypatch.delenv("PROJET_ADMIN_ACCESS_CODE", raising=False)
    assert authenticate_admin_code(session, "anything") is None
    get_settings.cache_clear()


def test_the_right_admin_code_bootstraps_and_signs_in(session, monkeypatch):
    from projet.config import get_settings
    from projet.services.auth import authenticate_admin_code

    monkeypatch.setenv("PROJET_ADMIN_ACCESS_CODE", "let-me-in")
    get_settings.cache_clear()

    assert session.query(PlatformUser).count() == 0
    subject_id = authenticate_admin_code(session, "let-me-in")
    assert subject_id is not None
    assert session.query(PlatformUser).count() == 1

    # A second use reuses the same bootstrapped user rather than creating another.
    again = authenticate_admin_code(session, "let-me-in")
    assert again == subject_id
    assert session.query(PlatformUser).count() == 1
    get_settings.cache_clear()


def test_the_wrong_admin_code_is_refused(session, monkeypatch):
    from projet.config import get_settings
    from projet.services.auth import authenticate_admin_code

    monkeypatch.setenv("PROJET_ADMIN_ACCESS_CODE", "let-me-in")
    get_settings.cache_clear()
    assert authenticate_admin_code(session, "wrong-code") is None
    get_settings.cache_clear()


def test_a_disabled_bootstrapped_admin_cannot_reauthenticate(session, monkeypatch):
    from projet.config import get_settings
    from projet.services.auth import authenticate_admin_code

    monkeypatch.setenv("PROJET_ADMIN_ACCESS_CODE", "let-me-in")
    get_settings.cache_clear()
    subject_id = authenticate_admin_code(session, "let-me-in")
    user = session.get(PlatformUser, subject_id)
    user.is_active = False
    session.flush()

    assert authenticate_admin_code(session, "let-me-in") is None
    get_settings.cache_clear()
