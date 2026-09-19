"""Curating the data pack, and who gets to see it.

The company owns its pack: it can add links and uploads, mark anything
confidential, exclude a resource without deleting it, or remove it outright.
Nothing in the pack is named on the public listing — participants only see
included company-supplied resources after a seat is accepted.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import DataPackResource, PlatformUser, Programme, Role
from projet.models.enums import ActorType, Provenance
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, start_session
from tests.conftest import make_participant, next_end, next_kickoff


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
def role_id(session, content_dir) -> str:
    seed_all(session, content_dir)
    return str(session.scalar(select(Role).where(Role.slug == "data-analytics")).id)


@pytest.fixture
def programme_id(client, session, admin, role_id) -> str:
    """A published challenge, so the public listing is reachable."""
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
    )
    assert company.status_code == 201, company.text
    created = client.post(
        "/programmes",
        json={
            "company_id": company.json()["id"],
            "role_id": role_id,
            "title": "Churn dashboard",
            "slug": "churn",
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 views, plus a half-page memo.",
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]
    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text
    return programme_id


def pack(client, programme_id) -> list[dict]:
    response = client.get(f"/programmes/{programme_id}/data-pack")
    assert response.status_code == 200, response.text
    return response.json()


def add_link(client, programme_id, **overrides) -> dict:
    payload = {
        "label": "Acme churn export",
        "url_or_storage_key": "https://acme.test/churn.csv",
        **overrides,
    }
    response = client.post(f"/programmes/{programme_id}/data-pack", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, programme_id, **fields) -> dict:
    response = client.post(
        f"/programmes/{programme_id}/data-pack/upload",
        files={"file": ("churn.csv", io.BytesIO(b"id,churned\n1,0\n"), "text/csv")},
        data={"label": "Q3 churn extract", **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_new_programme_starts_with_an_empty_pack(client, programme_id):
    assert pack(client, programme_id) == []


def test_a_company_resource_can_be_excluded_then_restored(client, programme_id):
    own = add_link(client, programme_id)

    excluded = client.patch(
        f"/programmes/{programme_id}/data-pack/{own['id']}",
        json={"included": False},
    )
    assert excluded.status_code == 200, excluded.text
    assert excluded.json()["included"] is False

    still_there = {entry["id"]: entry for entry in pack(client, programme_id)}
    assert still_there[own["id"]]["included"] is False

    restored = client.patch(
        f"/programmes/{programme_id}/data-pack/{own['id']}",
        json={"included": True},
    )
    assert restored.json()["included"] is True


def test_a_company_resource_can_be_deleted_outright(client, programme_id):
    own = add_link(client, programme_id)
    assert own["uploaded"] is True

    removed = client.delete(f"/programmes/{programme_id}/data-pack/{own['id']}")
    assert removed.status_code == 204
    assert own["id"] not in {entry["id"] for entry in pack(client, programme_id)}


def test_an_uploaded_file_is_served_through_a_signed_link(client, programme_id):
    entry = upload(client, programme_id)
    assert entry["url"].startswith("/files/data-pack/")
    assert "sig=" in entry["url"]

    path, _, query = entry["url"].partition("?")
    fetched = client.get(path, params=dict(pair.split("=", 1) for pair in query.split("&")))
    assert fetched.status_code == 200
    assert b"churned" in fetched.content

    # The signature is what makes it reachable, so without one it is not.
    assert client.get(path).status_code == 422


def test_an_unaccepted_file_type_is_refused(client, programme_id):
    response = client.post(
        f"/programmes/{programme_id}/data-pack/upload",
        files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert response.status_code == 422


def test_a_confidential_resource_puts_the_programme_behind_an_acknowledgement(
    client, session, programme_id
):
    before = client.get(f"/programmes/{programme_id}").json()
    assert before["requires_confidentiality_ack"] is False

    entry = upload(client, programme_id, confidential="true")
    assert entry["confidential"] is True
    session.expire_all()
    after = client.get(f"/programmes/{programme_id}").json()
    assert after["requires_confidentiality_ack"] is True

    client.delete(f"/programmes/{programme_id}/data-pack/{entry['id']}")
    session.expire_all()
    cleared = client.get(f"/programmes/{programme_id}").json()
    assert cleared["requires_confidentiality_ack"] is False


def test_excluding_the_last_confidential_resource_lifts_the_acknowledgement(
    client, session, programme_id
):
    entry = add_link(client, programme_id, confidential=True)
    session.expire_all()
    assert client.get(f"/programmes/{programme_id}").json()["requires_confidentiality_ack"]

    client.patch(
        f"/programmes/{programme_id}/data-pack/{entry['id']}",
        json={"included": False},
    )
    session.expire_all()
    assert not client.get(f"/programmes/{programme_id}").json()["requires_confidentiality_ack"]


def test_the_public_listing_never_names_the_data_pack(client, programme_id):
    add_link(client, programme_id, label="Acme internal churn export")
    upload(client, programme_id, label="Q3 revenue by account", confidential="true")

    listing = client.get("/public/x/acme/churn")
    assert listing.status_code == 200, listing.text
    assert listing.json()["data_pack_preview"] == []


def test_legacy_public_sources_are_hidden_from_the_company_pack(
    client, session, programme_id
):
    programme = session.get(Programme, uuid.UUID(programme_id))
    session.add(
        DataPackResource(
            programme_id=programme.id,
            label="data.gov.sg",
            provenance=Provenance.PUBLIC,
            included=True,
        )
    )
    session.flush()

    assert pack(client, programme_id) == []


def test_repointing_an_upload_is_refused(client, programme_id):
    entry = upload(client, programme_id)
    response = client.patch(
        f"/programmes/{programme_id}/data-pack/{entry['id']}",
        json={"url_or_storage_key": "https://elsewhere.test/x.csv"},
    )
    assert response.status_code == 409
    assert "Upload a new file" in response.json()["detail"]


def test_a_resource_from_another_programme_is_not_reachable(client, session, programme_id):
    other = DataPackResource(programme_id=None, label="Loose registry row")
    session.add(other)
    session.flush()
    response = client.patch(
        f"/programmes/{programme_id}/data-pack/{other.id}",
        json={"included": False},
    )
    assert response.status_code == 404


def test_the_participant_dashboard_gets_the_included_pack_with_links(
    client, session, programme_id
):
    upload(client, programme_id, label="Q3 churn extract", confidential="true")
    dropped = add_link(client, programme_id, label="Superseded extract")
    client.patch(
        f"/programmes/{programme_id}/data-pack/{dropped['id']}",
        json={"included": False},
    )
    # Legacy public rows must not reach participants.
    programme = session.get(Programme, uuid.UUID(programme_id))
    session.add(
        DataPackResource(
            programme_id=programme.id,
            label="data.gov.sg",
            provenance=Provenance.PUBLIC,
            included=True,
        )
    )
    session.flush()

    participant = make_participant(session, programme)
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)

    entries = client.get("/me/dashboard").json()["data_pack"]
    labels = {entry["label"]: entry for entry in entries}
    assert "Superseded extract" not in labels
    assert "data.gov.sg" not in labels
    confidential = labels["Q3 churn extract"]
    assert confidential["confidential"] is True
    assert confidential["url"].startswith("/files/data-pack/")
    assert "sig=" in confidential["url"]
