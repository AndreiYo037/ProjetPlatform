"""Login, password reset, and account setup over HTTP.

FR-013's deep-link behaviour is preserved through `next`, but the credential
itself is a password now, not possession of an inbox.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models.enums import AccountActionPurpose, ActorType
from projet.outbox.worker import run_once
from projet.services.auth import SESSION_COOKIE, issue_account_action_token, set_password


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


def _raw_token_for(session, actor_type, subject_id, email, purpose):
    _, raw = issue_account_action_token(
        session,
        actor_type=actor_type,
        subject_id=subject_id,
        email=email,
        purpose=purpose,
    )
    session.commit()
    return raw


# -- login ----------------------------------------------------------------


def test_logging_in_with_the_right_password_signs_you_in(client, session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()

    response = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter22", "actor_type": "company_user"},
    )

    assert response.status_code == 200
    assert response.json()["actor_type"] == "company_user"
    assert SESSION_COOKIE in response.cookies

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(rep.id)


def test_the_wrong_password_is_refused(client, session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()

    response = client.post(
        "/auth/login", json={"email": rep.email, "password": "wrong", "actor_type": "company_user"}
    )
    assert response.status_code == 401


def test_an_account_with_no_password_yet_cannot_log_in(client, rep):
    response = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "anything", "actor_type": "company_user"},
    )
    assert response.status_code == 401


def test_an_unknown_address_gets_the_same_error_as_a_wrong_password(client):
    """The point is that the two cases are indistinguishable from outside."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@nowhere.test", "password": "anything", "actor_type": "company_user"},
    )
    assert response.status_code == 401


def test_me_requires_a_session(client):
    assert client.get("/auth/me").status_code == 401


def test_session_probe_is_unauthenticated(client):
    response = client.get("/auth/session")
    assert response.status_code == 200
    assert response.json() is None


def test_logging_out_ends_the_session(client, session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()
    client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter22", "actor_type": "company_user"},
    )
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401


# -- setting a password on a freshly invited account -----------------------


def test_setting_the_initial_password_signs_you_in(client, session, rep):
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.SET_PASSWORD
    )

    response = client.post("/auth/password/set", json={"token": raw, "password": "hunter22"})

    assert response.status_code == 200
    assert SESSION_COOKIE in response.cookies
    assert client.get("/auth/me").status_code == 200

    # And the password now works for an ordinary login too.
    client.post("/auth/logout")
    login = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter22", "actor_type": "company_user"},
    )
    assert login.status_code == 200


def test_a_short_password_is_refused_at_setup(client, session, rep):
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.SET_PASSWORD
    )
    response = client.post("/auth/password/set", json={"token": raw, "password": "short"})
    assert response.status_code == 422


def test_a_replayed_set_password_token_is_refused(client, session, rep):
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.SET_PASSWORD
    )
    first = client.post("/auth/password/set", json={"token": raw, "password": "hunter22"})
    assert first.status_code == 200

    second = client.post("/auth/password/set", json={"token": raw, "password": "hunter23"})
    assert second.status_code == 400
    assert "already been used" in second.json()["detail"]


def test_a_reset_token_is_refused_at_the_set_password_endpoint(client, session, rep):
    """The two token purposes must not be interchangeable."""
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.RESET_PASSWORD
    )
    response = client.post("/auth/password/set", json={"token": raw, "password": "hunter22"})
    assert response.status_code == 400


# -- forgot / reset password -------------------------------------------------


def test_requesting_a_reset_queues_an_email_for_a_known_address(client, session, google, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()

    response = client.post(
        "/auth/password/forgot", json={"email": rep.email, "actor_type": "company_user"}
    )
    assert response.status_code == 200
    assert response.json()["sent"] is True

    run_once(session, google)
    sent = google.calls_of("send_email")
    assert len(sent) == 1
    assert sent[0].payload["to"] == rep.email


def test_requesting_a_reset_for_an_unknown_address_sends_nothing(client, session, google):
    response = client.post(
        "/auth/password/forgot", json={"email": "nobody@nowhere.test", "actor_type": "company_user"}
    )
    assert response.status_code == 200
    assert response.json()["sent"] is True  # identical response either way

    run_once(session, google)
    assert google.calls_of("send_email") == []


def test_resetting_with_a_valid_token_changes_the_password(client, session, rep):
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.RESET_PASSWORD
    )

    response = client.post("/auth/password/reset", json={"token": raw, "password": "hunter23"})
    assert response.status_code == 200
    assert SESSION_COOKIE in response.cookies

    client.post("/auth/logout")
    old = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter22", "actor_type": "company_user"},
    )
    new = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter23", "actor_type": "company_user"},
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_a_replayed_reset_token_is_refused(client, session, rep):
    raw = _raw_token_for(
        session, ActorType.COMPANY_USER, rep.id, rep.email, AccountActionPurpose.RESET_PASSWORD
    )
    client.post("/auth/password/reset", json={"token": raw, "password": "hunter22"})
    second = client.post("/auth/password/reset", json={"token": raw, "password": "hunter23"})
    assert second.status_code == 400


def test_an_expired_reset_token_is_refused(client, session, rep):
    from projet.models.base import utcnow

    token, raw = issue_account_action_token(
        session,
        actor_type=ActorType.COMPANY_USER,
        subject_id=rep.id,
        email=rep.email,
        purpose=AccountActionPurpose.RESET_PASSWORD,
    )
    token.expires_at = utcnow()
    session.commit()

    response = client.post("/auth/password/reset", json={"token": raw, "password": "hunter22"})
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]


def test_logging_in_as_the_wrong_actor_type_is_refused_over_http(client, session, rep):
    """The email and password are right, but this is the participant portal -
    a company account must not sign in through it."""
    set_password(session, ActorType.COMPANY_USER, rep.id, "hunter22")
    session.commit()

    response = client.post(
        "/auth/login",
        json={"email": rep.email, "password": "hunter22", "actor_type": "participant"},
    )
    assert response.status_code == 401
