"""Admitting applicants: who may, and how to reach one without real email.

Company self-serve is the default (CLAUDE.md): a company runs its own
programme, and deciding who gets a seat is part of running it, not something
that has to be routed through platform staff. This proves the company's own
manager can offer, waitlist and reject on their own programme.

It also proves the offer link is reachable from the application detail once
an offer goes out — because FR-401's tokenised accept flow depends on an
email actually arriving, and the fake Google driver every dev environment
runs against never delivers one anywhere. Without the link surfaced here,
"admit" and "the participant shows up" are two steps with nothing bridging
them.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import CompanyUser, PlatformUser, Role
from projet.models.enums import ActorType, CompanyUserRole
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, hash_password, start_session
from tests.conftest import scheduled


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


@pytest.fixture
def admin(session) -> PlatformUser:
    user = PlatformUser(name="Andrei", email="andrei@projet.sg")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def role(session, content_dir) -> Role:
    seed_all(session, content_dir)
    return session.scalar(select(Role).where(Role.slug == "data-analytics"))


@pytest.fixture
def rig(client, session, admin, role) -> dict:
    """A published programme with one company owner and one applicant."""
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme",
            "owner_name": "Owner",
            "owner_email": "owner@acme.test",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(role.id),
            "title": "Churn dashboard",
            "slug": "churn",
            **scheduled(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 views, plus a half-page memo.",
        },
    ).json()
    assert client.post(f"/programmes/{programme['id']}/publish").status_code == 200
    client.cookies.clear()

    owner = session.scalar(select(CompanyUser).where(CompanyUser.email == "owner@acme.test"))
    owner.password_hash = hash_password("ownerpass1")
    session.flush()

    applied = client.post(
        "/public/x/acme/churn/apply",
        data={
            "name": "Sam Student",
            "contact_email": "sam@school.edu.sg",
            "google_email": "sam@gmail.com",
            "writeup": " ".join(["analysis"] * 220),
            "availability_confirmed": "true",
            "password": "hunter2222",
        },
        files={"cv": ("sam.pdf", io.BytesIO(b"%PDF-1.4 cv"), "application/pdf")},
    )
    assert applied.status_code == 201, applied.text

    return {"programme_id": programme["id"], "owner_id": owner.id}


def sign_in(client, session, actor_type: ActorType, subject_id) -> None:
    _, raw = start_session(session, actor_type=actor_type, subject_id=subject_id)
    client.cookies.set(SESSION_COOKIE, raw)


def application_id(client, programme_id: str) -> str:
    return client.get(f"/programmes/{programme_id}/applications").json()[0]["id"]


def test_a_company_owner_can_admit_their_own_applicant(client, session, rig):
    sign_in(client, session, ActorType.COMPANY_USER, rig["owner_id"])
    app_id = application_id(client, rig["programme_id"])

    offered = client.post(
        f"/programmes/{rig['programme_id']}/applications/disposition",
        json={"application_ids": [app_id], "action": "offer"},
    )
    assert offered.status_code == 200, offered.text
    assert offered.json()["updated"] == 1


def test_a_rep_without_manager_rights_cannot_admit(client, session, rig):
    sign_in(client, session, ActorType.COMPANY_USER, rig["owner_id"])
    app_id = application_id(client, rig["programme_id"])

    rep = CompanyUser(
        company_id=session.get(CompanyUser, rig["owner_id"]).company_id,
        name="Rep",
        email="rep@acme.test",
        role=CompanyUserRole.REP,
        password_hash=hash_password("reppass123"),
    )
    session.add(rep)
    session.flush()

    client.cookies.clear()
    sign_in(client, session, ActorType.COMPANY_USER, rep.id)

    refused = client.post(
        f"/programmes/{rig['programme_id']}/applications/disposition",
        json={"application_ids": [app_id], "action": "offer"},
    )
    # 404 rather than 403 (FR-015): an unassigned rep should not learn a
    # programme exists just by being refused on it.
    assert refused.status_code == 404


def test_the_offer_link_appears_once_an_offer_is_made(client, session, rig):
    """This is the bridge across the two-step accept flow: without it, an
    admitted applicant depends entirely on an email that the fake Google
    driver never actually sends anywhere reachable in dev."""
    sign_in(client, session, ActorType.COMPANY_USER, rig["owner_id"])
    app_id = application_id(client, rig["programme_id"])

    before = client.get(f"/programmes/{rig['programme_id']}/applications/{app_id}").json()
    assert before["offer_url"] is None

    client.post(
        f"/programmes/{rig['programme_id']}/applications/disposition",
        json={"application_ids": [app_id], "action": "offer"},
    )

    after = client.get(f"/programmes/{rig['programme_id']}/applications/{app_id}").json()
    assert after["offer_url"] is not None
    assert "/accept?token=" in after["offer_url"]

    accepted = client.post("/accept", json={"token": after["offer_url"].split("token=")[1]})
    assert accepted.status_code == 200, accepted.text

    # Spent on use, same as the emailed link would be.
    reread = client.get(f"/programmes/{rig['programme_id']}/applications/{app_id}").json()
    assert reread["offer_url"] is None
