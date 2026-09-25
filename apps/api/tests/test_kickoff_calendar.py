"""Kickoff Calendar event creation.

Publishing a programme creates the Meet. Participants are not added as
attendees — they get the link in email and on the dashboard.
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
from projet.models import Application, PlatformUser, Programme, Role
from projet.models.enums import ActorType
from projet.outbox.worker import run_once
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, start_session
from tests.conftest import kickoff_on, next_kickoff, scheduled


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
def seeded(session, content_dir):
    seed_all(session, content_dir)
    return session.scalar(select(Role).where(Role.slug == "data-analytics"))


def sign_in(client, session, actor_type, subject_id):
    _, raw = start_session(session, actor_type=actor_type, subject_id=subject_id)
    client.cookies.set(SESSION_COOKIE, raw)


def programme_payload(company_id, role_id, *, title, slug, start=None, hour=14):
    start = start or next_kickoff()
    return {
        "company_id": company_id,
        "role_id": str(role_id),
        "title": title,
        "slug": slug,
        **scheduled(start, hour),
        "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "problem_statement": "Test problem",
        "deliverable_spec": "Test deliverable",
    }


def test_publish_creates_kickoff_event(client, session, google, admin, seeded):
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme-cal",
            "owner_name": "Owner",
            "owner_email": "owner@acme-cal.test",
        },
    ).json()
    start = next_kickoff()
    programme = client.post(
        "/programmes",
        json=programme_payload(
            company["id"],
            seeded.id,
            title="Calendar test",
            slug="cal-test",
            start=start,
            hour=14,
        ),
    ).json()

    published = client.post(f"/programmes/{programme['id']}/publish")
    assert published.status_code == 200
    assert published.json()["kickoff_meet_link"]

    create_calls = google.calls_of("create_event")
    assert len(create_calls) == 1
    assert "Kickoff" in create_calls[0].payload["body"]["summary"]
    assert "Acme" in create_calls[0].payload["body"]["summary"]
    begins = datetime.fromisoformat(create_calls[0].payload["body"]["start"]["dateTime"])
    ends = datetime.fromisoformat(create_calls[0].payload["body"]["end"]["dateTime"])
    meeting = kickoff_on(start, 14)
    assert begins == meeting
    assert ends == meeting + timedelta(hours=1)

    prog = session.get(Programme, uuid.UUID(programme["id"]))
    assert prog.kickoff_event_id is not None


def test_accept_does_not_add_participant_to_kickoff_event(
    client, session, google, admin, seeded
):
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme-cal2",
            "owner_name": "Owner",
            "owner_email": "owner@acme-cal2.test",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json=programme_payload(
            company["id"],
            seeded.id,
            title="Calendar accept test",
            slug="cal-accept",
        ),
    ).json()
    programme_id = programme["id"]

    client.post(f"/programmes/{programme_id}/publish")
    run_once(session, google)

    # Apply as a stranger
    client.cookies.clear()
    applied = client.post(
        "/public/x/acme-cal2/cal-accept/apply",
        data={
            "name": "Sam Student",
            "contact_email": "sam-cal@school.edu.sg",
            "google_email": "sam-cal@gmail.com",
            "writeup": " ".join(["analysis"] * 220),
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
            "password": "hunter22",
        },
        files={"cv": ("sam.pdf", io.BytesIO(b"%PDF-1.4 cv"), "application/pdf")},
    )
    assert applied.status_code == 201

    run_once(session, google)

    # Offer
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    applications = client.get(f"/programmes/{programme_id}/applications").json()
    application_id = applications[0]["id"]
    client.post(
        f"/programmes/{programme_id}/applications/disposition",
        json={"application_ids": [application_id], "action": "offer"},
    )

    # Accept
    application = session.get(Application, uuid.UUID(application_id))
    token = application.offer_token
    client.cookies.clear()
    accepted = client.post("/accept", json={"token": token})
    assert accepted.status_code == 200

    run_once(session, google)

    assert google.calls_of("patch_event_attendees") == []


def test_the_offer_carries_the_meet_link_without_a_calendar_invite(
    client, session, google, admin, seeded
):
    """The Meet link lands in the offer email. Participants are not invited
    on Calendar.
    """
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme-cal4",
            "owner_name": "Owner",
            "owner_email": "owner@acme-cal4.test",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json=programme_payload(
            company["id"],
            seeded.id,
            title="Offer invite test",
            slug="cal-offer",
        ),
    ).json()
    programme_id = programme["id"]

    client.post(f"/programmes/{programme_id}/publish")
    prog = session.get(Programme, uuid.UUID(programme_id))
    assert prog.kickoff_meet_link, "publishing puts a Meet link on standby"

    client.cookies.clear()
    client.post(
        "/public/x/acme-cal4/cal-offer/apply",
        data={
            "name": "Sam Student",
            "contact_email": "sam-offer@school.edu.sg",
            "google_email": "sam-offer@gmail.com",
            "writeup": " ".join(["analysis"] * 220),
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
            "password": "hunter22",
        },
        files={"cv": ("sam.pdf", io.BytesIO(b"%PDF-1.4 cv"), "application/pdf")},
    )

    sign_in(client, session, ActorType.PLATFORM, admin.id)
    applications = client.get(f"/programmes/{programme_id}/applications").json()
    client.post(
        f"/programmes/{programme_id}/applications/disposition",
        json={"application_ids": [applications[0]["id"]], "action": "offer"},
    )
    run_once(session, google)

    offer = next(
        c for c in google.calls_of("send_email") if c.payload["subject"].startswith("You're in")
    )
    assert prog.kickoff_meet_link in offer.payload["html_body"]
    assert "Offer invite test" in offer.payload["html_body"]
    body = offer.payload["html_body"]
    assert "<strong>Kickoff:</strong>" in body
    assert "14:00 SGT" in body
    assert "00:00" not in body
    assert "calendar invite" not in body.lower()
    assert google.calls_of("patch_event_attendees") == []


def test_republish_does_not_create_duplicate_event(
    client, session, google, admin, seeded
):
    """ensure_kickoff_event is idempotent — a second publish reuses the event."""
    sign_in(client, session, ActorType.PLATFORM, admin.id)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme-cal3",
            "owner_name": "Owner",
            "owner_email": "owner@acme-cal3.test",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json=programme_payload(
            company["id"],
            seeded.id,
            title="Idempotent test",
            slug="cal-idem",
        ),
    ).json()
    programme_id = programme["id"]

    client.post(f"/programmes/{programme_id}/publish")
    assert len(google.calls_of("create_event")) == 1

    # Calling ensure_kickoff_event again should not create a second event
    from projet.services.calendar import ensure_kickoff_event

    prog = session.get(Programme, uuid.UUID(programme_id))
    ensure_kickoff_event(session, prog)
    assert len(google.calls_of("create_event")) == 1
