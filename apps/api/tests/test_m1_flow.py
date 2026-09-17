"""Milestone 1 end to end, over HTTP.

The path a real cohort takes: admin creates a company, the owner signs in and
invites a rep, admin sets up a programme against a seeded role, publishes it, a
stranger reads the public page and applies, admin screens and offers, the
applicant accepts, and provisioning fires.
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import Application, PlatformUser, Role
from projet.models.enums import ActorType
from projet.outbox.worker import run_once
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


def writeup(words: int = 220) -> str:
    return " ".join(["analysis"] * words)


@pytest.fixture
def seeded(session, content_dir):
    seed_all(session, content_dir)
    return session.scalar(select(Role).where(Role.slug == "data-analytics"))


def test_the_full_funnel(client, session, google, admin, seeded, content_dir):
    # -- admin creates the company and its owner ------------------------------
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    created = client.post(
        "/companies",
        json={
            "name": "Acme Pte Ltd",
            "slug": "acme",
            "owner_name": "Dana Owner",
            "owner_email": "dana@acme.sg",
        },
    )
    assert created.status_code == 201
    company_id = created.json()["id"]

    # -- the role picker shows what the role commits them to (FR-053) ---------
    clusters = client.get("/roles/clusters").json()
    assert len(clusters) == 11
    found = client.get("/roles/search", params={"q": "BI"}).json()
    assert any(r["slug"] == "data-analytics" for r in found), "aliases must be searchable"

    implications = client.get(f"/roles/{seeded.id}/implications").json()
    assert implications["default_deliverable"].startswith("Dashboard")
    assert len(implications["judging_criteria"]) == 4
    assert implications["company_asks_easy"]

    # -- programme setup ------------------------------------------------------
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    programme = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": str(seeded.id),
            "title": "Churn dashboard",
            "slug": "churn",
            "capacity": 1,
            "applications_close_at": (now + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 decision-relevant views, plus a half-page memo.",
        },
    )
    assert programme.status_code == 201
    programme_id = programme.json()["id"]

    # The rubric arrives pre-filled: universal slots 1 and 4, role slots 2 and 3.
    criteria = programme.json()["criteria"]
    assert [c["slot"] for c in criteria] == [1, 2, 3, 4]
    assert criteria[0]["name"] == "Problem understanding"
    assert criteria[1]["name"] == "Data handling"
    assert all(c["anchor_5"] for c in criteria)

    # The data pack is seeded from the role's registry, provenance visible.
    data_pack = client.get(f"/programmes/{programme_id}/data-pack").json()
    assert data_pack and all(r["provenance"] == "public" for r in data_pack)

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is True, check["problems"]

    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "open"

    # -- a stranger reads the listing and applies ----------------------------
    client.cookies.clear()
    listing = client.get("/public/x/acme/churn")
    assert listing.status_code == 200
    body = listing.json()
    assert body["state"] == "open"
    assert body["seats_total"] == 1
    # FR-078 — the full rubric is published, all four criteria with anchors.
    assert len(body["criteria"]) == 4
    assert all(c["anchor_5"] and c["anchor_3"] and c["anchor_1"] for c in body["criteria"])

    applied = client.post(
        "/public/x/acme/churn/apply",
        data={
            "name": "Sam Student",
            "contact_email": "sam@school.edu.sg",
            "google_email": "sam@gmail.com",
            "organisation": "NUS",
            "year_course": "Y2 Business Analytics",
            "writeup": writeup(),
            "linkedin_url": "https://www.linkedin.com/in/sam-student",
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
            "password": "hunter22",
        },
        files={"cv": ("sam.pdf", io.BytesIO(b"%PDF-1.4 cv"), "application/pdf")},
    )
    assert applied.status_code == 201, applied.text
    assert applied.json()["google_email_warning"] is None

    run_once(session, google)
    # The owner's set-password email queued at company creation, plus the
    # applicant's confirmation, queued at apply time.
    assert len(google.calls_of("send_email")) == 2, "confirmation email sends immediately"

    # -- admin screens and offers --------------------------------------------
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    applications = client.get(f"/programmes/{programme_id}/applications").json()
    assert len(applications) == 1
    application_id = applications[0]["id"]

    detail = client.get(f"/programmes/{programme_id}/applications/{application_id}").json()
    assert detail["writeup"]
    assert detail["linkedin_url"].endswith("/sam-student")
    assert detail["availability_confirmed"] is True
    assert detail["cv_url"] and "sig=" in detail["cv_url"], "CVs are served signed"

    scored = client.patch(
        f"/programmes/{programme_id}/applications/{application_id}/score",
        json={"relevance": 5, "specificity": 4, "capability": 4, "followthrough": 4},
    )
    assert scored.json()["score_total"] == 17

    offered = client.post(
        f"/programmes/{programme_id}/applications/disposition",
        json={"application_ids": [application_id], "action": "offer"},
    )
    assert offered.json()["updated"] == 1

    # -- the applicant accepts ------------------------------------------------
    application = session.get(Application, uuid.UUID(application_id))
    token = application.offer_token
    assert token

    client.cookies.clear()
    accepted = client.post("/accept", json={"token": token})
    assert accepted.status_code == 200, accepted.text
    assert "confirmed" in accepted.json()["message"]

    run_once(session, google)
    # The welcome email is queued by the provisioning chain.
    assert len(google.calls_of("send_email")) >= 2

    sign_in(client, session, ActorType.PLATFORM, admin.id)
    seats = client.get(f"/programmes/{programme_id}/seats").json()
    assert seats["taken"] == 1
    assert seats["remaining"] == 0


def test_a_draft_programme_is_not_publicly_reachable(client, session, admin, seeded):
    """FR-056 — programmes start in draft and are not publicly reachable."""
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Quiet Co",
            "slug": "quiet",
            "owner_name": "Owner",
            "owner_email": "owner@quiet.sg",
        },
    ).json()
    client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Unpublished",
            "slug": "secret",
        },
    )
    client.cookies.clear()
    assert client.get("/public/x/quiet/secret").status_code == 404


def test_publication_is_blocked_by_an_incomplete_rubric(client, session, admin, seeded):
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Half Co",
            "slug": "half",
            "owner_name": "Owner",
            "owner_email": "owner@half.sg",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Half configured",
            "slug": "half-prog",
        },
    ).json()

    criterion = programme["criteria"][2]
    client.patch(
        f"/programmes/{programme['id']}/criteria/{criterion['id']}",
        json={"anchor_1": ""},
    )
    check = client.get(f"/programmes/{programme['id']}/publication-check").json()
    assert check["ready"] is False


def test_a_universal_criterion_cannot_be_renamed_over_http(client, session, admin, seeded):
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Fixed Co",
            "slug": "fixed",
            "owner_name": "Owner",
            "owner_email": "owner@fixed.sg",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Fixed",
            "slug": "fixed-prog",
        },
    ).json()
    slot_one = programme["criteria"][0]

    response = client.patch(
        f"/programmes/{programme['id']}/criteria/{slot_one['id']}",
        json={"name": "Bespoke"},
    )
    assert response.status_code == 409
    assert "cannot be renamed" in response.json()["detail"]


def test_the_writeup_has_no_word_range(client, session, admin, seeded):
    """FR-205's 200-300 word range was removed: any non-empty writeup is
    accepted, short or long."""
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Words Co",
            "slug": "words",
            "owner_name": "Owner",
            "owner_email": "owner@words.sg",
        },
    ).json()
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Words",
            "slug": "words-prog",
            "applications_close_at": (now + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 decision-relevant views, plus a half-page memo.",
        },
    ).json()
    client.post(f"/programmes/{programme['id']}/publish")
    client.cookies.clear()

    response = client.post(
        "/public/x/words/words-prog/apply",
        data={
            "name": "Brief Person",
            "contact_email": "brief@school.edu.sg",
            "google_email": "brief@gmail.com",
            "writeup": "Too short.",
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "password": "hunter22",
        },
        files={"cv": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 201, response.text


def test_an_application_can_decline_both_consents(client, session, admin, seeded):
    """FR-202 — submission is allowed with either declined. Declining is a real
    choice, not a soft block."""
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Consent Co",
            "slug": "consent",
            "owner_name": "Owner",
            "owner_email": "owner@consent.sg",
        },
    ).json()
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Consent",
            "slug": "consent-prog",
            "applications_close_at": (now + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 decision-relevant views, plus a half-page memo.",
        },
    ).json()
    client.post(f"/programmes/{programme['id']}/publish")
    client.cookies.clear()

    response = client.post(
        "/public/x/consent/consent-prog/apply",
        data={
            "name": "Private Person",
            "contact_email": "private@school.edu.sg",
            "google_email": "private@gmail.com",
            "writeup": writeup(),
            "availability_confirmed": "true",
            "consent_share_company": "false",
            "consent_recording": "false",
            "password": "hunter22",
        },
        files={"cv": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 201

    # And they must not appear in anything company-facing.
    from projet.access import company_visible_applications

    visible = list(session.scalars(company_visible_applications(uuid.UUID(programme["id"]))))
    assert visible == []


def test_a_non_google_address_warns_without_blocking(client, session, admin, seeded):
    """FR-204 — warning, not a hard block."""
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Warn Co",
            "slug": "warn",
            "owner_name": "Owner",
            "owner_email": "owner@warn.sg",
        },
    ).json()
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Warn",
            "slug": "warn-prog",
            "applications_close_at": (now + timedelta(days=2)).isoformat(),
            "start_at": next_kickoff().isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 decision-relevant views, plus a half-page memo.",
        },
    ).json()
    client.post(f"/programmes/{programme['id']}/publish")
    client.cookies.clear()

    response = client.post(
        "/public/x/warn/warn-prog/apply",
        data={
            "name": "Outlook Person",
            "contact_email": "person@school.edu.sg",
            "google_email": "person@outlook.com",
            "writeup": writeup(),
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "password": "hunter22",
        },
        files={"cv": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 201, "a warning must not block the application"
    assert "outlook.com" in response.json()["google_email_warning"]
