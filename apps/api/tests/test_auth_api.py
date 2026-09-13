"""The sign-in flow over HTTP.

FR-011: requesting a link and clicking it is the whole flow.
FR-013: an email link deep-links straight to the target screen, authenticating
on the way — a rep clicking "score now" lands on the candidate card, signed in.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import MagicLinkToken, Outbox
from projet.outbox.worker import run_once
from projet.services.auth import SESSION_COOKIE


@pytest.fixture
def client(session, google) -> TestClient:
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


def _link_for(session, google, client, email: str, next_path: str | None = None) -> str:
    """Run the request half of the flow and pull the raw token out of the email."""
    body = {"email": email}
    if next_path:
        body["next"] = next_path
    client.post("/auth/magic-link", json=body)
    run_once(session, google)

    call = google.calls_of("send_email")[-1]
    assert call.payload["to"] == email
    row = session.scalars(select(Outbox).order_by(Outbox.created_at.desc())).first()
    url = row.payload["url"]
    return url.split("token=")[1].split("&")[0]


def test_requesting_a_link_sends_one(client, session, google, rep):
    response = client.post("/auth/magic-link", json={"email": rep.email})
    assert response.status_code == 200
    assert response.json()["sent"] is True

    run_once(session, google)
    assert len(google.calls_of("send_email")) == 1


def test_an_unknown_address_gets_the_same_answer_and_no_email(client, session, google):
    """A different response here enumerates who has an account."""
    known = client.post("/auth/magic-link", json={"email": "nobody@nowhere.test"})
    assert known.status_code == 200
    assert known.json()["sent"] is True

    run_once(session, google)
    assert google.calls_of("send_email") == []


def test_clicking_the_link_signs_you_in(client, session, google, rep):
    raw = _link_for(session, google, client, rep.email)
    response = client.post("/auth/verify", json={"token": raw})

    assert response.status_code == 200
    assert response.json()["actor"]["email"] == rep.email
    assert response.json()["actor"]["actor_type"] == "company_user"
    assert SESSION_COOKIE in response.cookies

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(rep.id)


def test_the_link_carries_you_to_where_you_were_going(client, session, google, rep):
    """FR-013 — the deep link is the point; landing on a sign-in page that
    forgot the destination is the failure."""
    raw = _link_for(session, google, client, rep.email, next_path="/score/abc")
    response = client.post("/auth/verify", json={"token": raw})

    assert response.json()["next"] == "/score/abc"


def test_an_absolute_redirect_is_refused(client, session, google, rep):
    """The link arrives by email and is easy to pass around; an open redirect
    here would be a phishing primitive."""
    raw = _link_for(session, google, client, rep.email, next_path="https://evil.test/steal")
    response = client.post("/auth/verify", json={"token": raw})

    assert response.json()["next"] is None


def test_a_protocol_relative_redirect_is_refused(client, session, google, rep):
    raw = _link_for(session, google, client, rep.email, next_path="//evil.test")
    assert client.post("/auth/verify", json={"token": raw}).json()["next"] is None


def test_a_replayed_link_is_refused(client, session, google, rep):
    """Email clients and scanners prefetch links, so this is not theoretical."""
    raw = _link_for(session, google, client, rep.email)
    assert client.post("/auth/verify", json={"token": raw}).status_code == 200

    second = client.post("/auth/verify", json={"token": raw})
    assert second.status_code == 400
    assert "already been used" in second.json()["detail"]


def test_me_requires_a_session(client):
    assert client.get("/auth/me").status_code == 401


def test_session_probe_is_unauthenticated(client):
    """So the frontend can render signed-out state without a 401 every load."""
    response = client.get("/auth/session")
    assert response.status_code == 200
    assert response.json() is None


def test_logging_out_ends_the_session(client, session, google, rep):
    raw = _link_for(session, google, client, rep.email)
    client.post("/auth/verify", json={"token": raw})
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_asking_twice_sends_two_distinct_links(client, session, google, rep):
    """The outbox is idempotent per subject, and each token is its own subject,
    so a second request genuinely sends a second email."""
    first = _link_for(session, google, client, rep.email)
    second = _link_for(session, google, client, rep.email)

    assert first != second
    assert len(google.calls_of("send_email")) == 2
    assert session.query(MagicLinkToken).count() == 2


def test_the_admin_code_endpoint_is_404_when_unconfigured(client, monkeypatch):
    from projet.config import get_settings

    monkeypatch.delenv("PROJET_ADMIN_ACCESS_CODE", raising=False)
    get_settings.cache_clear()
    response = client.post("/auth/admin-code", json={"code": "anything"})
    assert response.status_code == 404
    get_settings.cache_clear()


def test_the_admin_code_endpoint_signs_in_and_sets_a_cookie(client, monkeypatch):
    from projet.config import get_settings

    monkeypatch.setenv("PROJET_ADMIN_ACCESS_CODE", "let-me-in")
    get_settings.cache_clear()

    response = client.post("/auth/admin-code", json={"code": "let-me-in"})
    assert response.status_code == 200
    assert response.json()["actor_type"] == "platform"
    assert SESSION_COOKIE in response.cookies

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["actor_type"] == "platform"
    get_settings.cache_clear()


def test_the_wrong_admin_code_is_rejected_over_http(client, monkeypatch):
    from projet.config import get_settings

    monkeypatch.setenv("PROJET_ADMIN_ACCESS_CODE", "let-me-in")
    get_settings.cache_clear()
    response = client.post("/auth/admin-code", json={"code": "nope"})
    assert response.status_code == 401
    get_settings.cache_clear()
