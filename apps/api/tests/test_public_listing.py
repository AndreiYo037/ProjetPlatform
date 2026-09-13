"""The challenge listing endpoints — FR-104 (one company) and FR-105 (the
platform-wide directory).

Neither existed in the original PRD; both reuse the same state/seat logic as
the single-programme page (FR-101/FR-102) so a browsing stranger and someone
who followed a direct link see a consistent story.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import PlatformUser, Role
from projet.models.enums import ActorType
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, start_session
from tests.conftest import next_kickoff


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


def sign_in(client, session, actor_type: ActorType, subject_id) -> None:
    _, raw = start_session(session, actor_type=actor_type, subject_id=subject_id)
    client.cookies.set(SESSION_COOKIE, raw)


@pytest.fixture
def roles(session, content_dir):
    seed_all(session, content_dir)
    return {
        "data-analytics": session.scalar(select(Role).where(Role.slug == "data-analytics")),
    }


def make_company(client, session, admin, *, name: str, slug: str) -> str:
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    created = client.post(
        "/companies",
        json={
            "name": name,
            "slug": slug,
            "owner_name": "Owner",
            "owner_email": f"owner@{slug}.test",
        },
    )
    assert created.status_code == 201
    return created.json()["id"]


def make_programme(
    client,
    session,
    admin,
    *,
    company_id: str,
    role_id,
    title: str,
    slug: str,
    capacity: int | None = None,
    publish: bool = True,
) -> str:
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    now = datetime.now(UTC)
    programme = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": str(role_id),
            "title": title,
            "slug": slug,
            "capacity": capacity,
            "applications_close_at": (now + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 decision-relevant views, plus a half-page memo.",
        },
    )
    assert programme.status_code == 201, programme.text
    programme_id = programme.json()["id"]
    if publish:
        published = client.post(f"/programmes/{programme_id}/publish")
        assert published.status_code == 200, published.text
    return programme_id


# -- company listing (FR-104) -----------------------------------------------


def test_a_companys_listing_includes_open_and_excludes_draft(client, session, admin, roles):
    company_id = make_company(client, session, admin, name="Acme", slug="acme")
    role_id = roles["data-analytics"].id
    make_programme(
        client, session, admin, company_id=company_id, role_id=role_id,
        title="Churn dashboard", slug="churn", capacity=2,
    )
    make_programme(
        client, session, admin, company_id=company_id, role_id=role_id,
        title="Unpublished", slug="draft-prog", publish=False,
    )

    client.cookies.clear()
    response = client.get("/public/x/acme")
    assert response.status_code == 200
    slugs = [row["programme_slug"] for row in response.json()]
    assert "churn" in slugs
    assert "draft-prog" not in slugs


def test_a_companys_listing_shows_seats_only_when_capacity_is_set(client, session, admin, roles):
    company_id = make_company(client, session, admin, name="Acme2", slug="acme2")
    role_id = roles["data-analytics"].id
    make_programme(
        client, session, admin, company_id=company_id, role_id=role_id,
        title="Capped", slug="capped", capacity=3,
    )
    make_programme(
        client, session, admin, company_id=company_id, role_id=role_id,
        title="Uncapped", slug="uncapped", capacity=None,
    )

    client.cookies.clear()
    rows = {r["programme_slug"]: r for r in client.get("/public/x/acme2").json()}
    assert rows["capped"]["seats_total"] == 3
    assert rows["capped"]["seats_remaining"] == 3
    assert rows["uncapped"]["seats_total"] is None
    assert rows["uncapped"]["seats_remaining"] is None


def test_an_unknown_company_slug_404s(client):
    assert client.get("/public/x/nobody-here").status_code == 404


# -- platform directory (FR-105) ---------------------------------------------


def test_the_directory_only_lists_open_programmes_across_companies(
    client, session, admin, roles
):
    role_id = roles["data-analytics"].id
    acme = make_company(client, session, admin, name="Acme3", slug="acme3")
    beta = make_company(client, session, admin, name="Beta", slug="beta")
    make_programme(
        client, session, admin, company_id=acme, role_id=role_id,
        title="Acme open", slug="acme-open",
    )
    make_programme(
        client, session, admin, company_id=beta, role_id=role_id,
        title="Beta draft", slug="beta-draft", publish=False,
    )

    client.cookies.clear()
    response = client.get("/public/challenges")
    assert response.status_code == 200
    body = response.json()
    slugs = {(row["company_slug"], row["programme_slug"]) for row in body}
    assert ("acme3", "acme-open") in slugs
    assert ("beta", "beta-draft") not in slugs
    assert all(row["state"] == "open" for row in body)


def test_the_directory_filters_by_role_slug(client, session, admin, roles):
    role_id = roles["data-analytics"].id
    acme = make_company(client, session, admin, name="Acme4", slug="acme4")
    make_programme(
        client, session, admin, company_id=acme, role_id=role_id,
        title="Filter me", slug="filter-me",
    )

    client.cookies.clear()
    matching = client.get("/public/challenges", params={"role_slug": "data-analytics"}).json()
    assert any(row["programme_slug"] == "filter-me" for row in matching)

    none_match = client.get("/public/challenges", params={"role_slug": "no-such-role"}).json()
    assert none_match == []


def test_the_directory_filters_by_cluster(client, session, admin, roles):
    role = roles["data-analytics"]
    acme = make_company(client, session, admin, name="Acme5", slug="acme5")
    make_programme(
        client, session, admin, company_id=acme, role_id=role.id,
        title="Clustered", slug="clustered",
    )

    client.cookies.clear()
    matching = client.get("/public/challenges", params={"cluster": role.cluster}).json()
    assert any(row["programme_slug"] == "clustered" for row in matching)

    none_match = client.get("/public/challenges", params={"cluster": "Not A Real Cluster"}).json()
    assert none_match == []


def test_the_directory_paginates(client, session, admin, roles):
    role_id = roles["data-analytics"].id
    acme = make_company(client, session, admin, name="Acme6", slug="acme6")
    for i in range(5):
        make_programme(
            client, session, admin, company_id=acme, role_id=role_id,
            title=f"Prog {i}", slug=f"prog-{i}",
        )

    client.cookies.clear()
    page1 = client.get("/public/challenges", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/public/challenges", params={"limit": 2, "offset": 2}).json()
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["programme_slug"] for r in page1}.isdisjoint({r["programme_slug"] for r in page2})
