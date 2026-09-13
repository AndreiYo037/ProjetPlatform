"""The company logo, and the website the drafting pass reads.

A logo is the one company-supplied file meant for strangers: it renders on the
public listing and the directory, both read without a session. So it is served
unsigned, which puts the whole burden on the upload - hence the type check, and
hence the assertion here that an SVG is refused rather than stored and served
from our own origin.
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
from projet.models import Company, PlatformUser, Role
from projet.models.enums import ActorType
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, start_session
from projet.storage import get_storage
from tests.conftest import next_kickoff

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c49444154789c63f8cfc00000030101003e1c2e4b0000000049454e44ae426082"
)


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
def company_id(client, session, admin) -> str:
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    created = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme",
            "owner_name": "Owner",
            "owner_email": "owner@acme.test",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def upload(client, company_id, *, name="logo.png", data=PNG, content_type="image/png"):
    return client.post(
        f"/companies/{company_id}/logo",
        files={"file": (name, io.BytesIO(data), content_type)},
    )


def test_a_logo_is_uploaded_and_served_without_a_signature(client, company_id):
    uploaded = upload(client, company_id)
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["logo_url"] == f"/companies/{company_id}/logo"

    # No cookie, no signature: this is the page a stranger loads.
    client.cookies.clear()
    served = client.get(f"/companies/{company_id}/logo")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == PNG


def test_an_svg_is_refused(client, company_id):
    """An SVG can carry script, and this route serves from our own origin."""
    response = upload(
        client,
        company_id,
        name="logo.svg",
        data=b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>",
        content_type="image/svg+xml",
    )
    assert response.status_code == 422
    assert "PNG" in response.json()["detail"]


def test_an_oversized_logo_is_refused(client, company_id):
    response = upload(client, company_id, data=b"\x89PNG" + b"0" * (2 * 1024 * 1024))
    assert response.status_code == 413


def test_replacing_a_logo_drops_the_old_object(client, session, company_id):
    first = upload(client, company_id)
    assert first.status_code == 201
    session.expire_all()
    old_key = session.scalar(select(Company.logo_url))

    second = upload(client, company_id, name="new.png")
    assert second.status_code == 201
    session.expire_all()
    new_key = session.scalar(select(Company.logo_url))
    assert new_key != old_key
    assert not get_storage().exists(old_key)
    assert get_storage().exists(new_key)


def test_removing_the_logo_clears_it_everywhere(client, company_id):
    upload(client, company_id)
    removed = client.delete(f"/companies/{company_id}/logo")
    assert removed.status_code == 200, removed.text
    assert removed.json()["logo_url"] is None
    assert client.get(f"/companies/{company_id}/logo").status_code == 404


def test_a_company_with_no_logo_has_no_route_to_serve(client, company_id):
    assert client.get(f"/companies/{company_id}/logo").status_code == 404


def test_the_website_is_editable_and_kept(client, company_id):
    updated = client.patch(
        f"/companies/{company_id}",
        json={"website_url": "  https://acme.test  "},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["website_url"] == "https://acme.test"

    cleared = client.patch(f"/companies/{company_id}", json={"website_url": ""})
    assert cleared.json()["website_url"] is None


def test_the_logo_reaches_the_public_listing_and_the_directory(
    client, session, company_id, content_dir
):
    seed_all(session, content_dir)
    role_id = str(session.scalar(select(Role).where(Role.slug == "data-analytics")).id)
    created = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "Churn dashboard",
            "slug": "churn",
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 views, plus a half-page memo.",
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    assert client.post(f"/programmes/{created.json()['id']}/publish").status_code == 200
    upload(client, company_id)

    client.cookies.clear()
    listing = client.get("/public/x/acme/churn")
    assert listing.status_code == 200, listing.text
    assert listing.json()["company_logo_url"] == f"/companies/{company_id}/logo"

    directory = client.get("/public/challenges")
    rows = directory.json()
    assert rows
    assert rows[0]["company_logo_url"] == f"/companies/{company_id}/logo"
