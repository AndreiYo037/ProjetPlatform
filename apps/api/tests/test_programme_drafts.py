"""Unpublished programmes live in Drafts, not the live listings, and can be deleted."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import CompanyUser, Programme
from projet.models.enums import ActorType, CompanyUserRole, ProgrammeStatus
from projet.services.auth import SESSION_COOKIE, start_session


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


@pytest.fixture
def manager(session, company) -> CompanyUser:
    user = CompanyUser(
        company_id=company.id,
        name="Mo Manager",
        email="mo@acme.test",
        role=CompanyUserRole.OWNER,
    )
    session.add(user)
    session.flush()
    return user


def sign_in_company(client, session, user: CompanyUser) -> None:
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=user.id)
    client.cookies.set(SESSION_COOKIE, raw)


def test_a_draft_is_listed_under_drafts_not_active(
    client, session, company, programme, manager, role
):
    draft = Programme(
        company_id=company.id,
        role_id=role.id,
        title="Unfinished brief",
        slug="unfinished-brief",
        status=ProgrammeStatus.DRAFT,
    )
    session.add(draft)
    session.flush()
    sign_in_company(client, session, manager)

    home = client.get(f"/companies/{company.id}/home").json()
    draft_ids = {row["id"] for row in home["draft_programmes"]}
    active_ids = {row["id"] for row in home["active_programmes"]}
    past_ids = {row["id"] for row in home["past_programmes"]}

    assert str(draft.id) in draft_ids
    assert str(draft.id) not in active_ids
    assert str(draft.id) not in past_ids
    assert str(programme.id) in active_ids
    assert str(programme.id) not in draft_ids


def test_a_draft_can_be_deleted(client, session, company, manager, role):
    draft = Programme(
        company_id=company.id,
        role_id=role.id,
        title="Scratch",
        slug="scratch",
        status=ProgrammeStatus.DRAFT,
    )
    session.add(draft)
    session.flush()
    sign_in_company(client, session, manager)

    removed = client.delete(f"/programmes/{draft.id}")
    assert removed.status_code == 204
    assert client.get(f"/programmes/{draft.id}").status_code == 404

    home = client.get(f"/companies/{company.id}/home").json()
    assert home["draft_programmes"] == []


def test_a_published_programme_cannot_be_deleted(client, session, programme, manager):
    sign_in_company(client, session, manager)
    refused = client.delete(f"/programmes/{programme.id}")
    assert refused.status_code == 409
    assert "draft" in refused.json()["detail"].lower()
    assert client.get(f"/programmes/{programme.id}").status_code == 200
