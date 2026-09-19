"""Kickoff Calendar event creation and attendee patching.

Publishing a programme creates the Calendar event. Accepting an offer adds the
participant as an attendee via the provisioning chain's KICKOFF_INVITE effect.
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
from tests.conftest import next_end, next_kickoff


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
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Calendar test",
            "slug": "cal-test",
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "Test problem",
            "deliverable_spec": "Test deliverable",
        },
    ).json()

    published = client.post(f"/programmes/{programme['id']}/publish")
    assert published.status_code == 200

    create_calls = google.calls_of("create_event")
    assert len(create_calls) == 1
    assert "Kickoff" in create_calls[0].payload["body"]["summary"]
    assert "Acme" in create_calls[0].payload["body"]["summary"]

    prog = session.get(Programme, uuid.UUID(programme["id"]))
    assert prog.kickoff_event_id is not None


def test_accept_adds_participant_to_kickoff_event(
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
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Calendar accept test",
            "slug": "cal-accept",
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "Test problem",
            "deliverable_spec": "Test deliverable",
        },
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

    # The kickoff event should have been patched with the participant
    patch_calls = google.calls_of("patch_event_attendees")
    kickoff_patches = [
        c for c in patch_calls
        if c.payload.get("add") and any(
            a.email == "sam-cal@gmail.com" for a in c.payload["add"]
        )
    ]
    assert len(kickoff_patches) >= 1, (
        f"expected kickoff event to be patched with participant; "
        f"got patch calls: {patch_calls}"
    )


def test_the_offer_carries_the_meet_link_and_a_calendar_invite(
    client, session, google, admin, seeded
):
    """The Meet link and the Calendar invite both land with the offer.

    Someone deciding whether to take a place checks the kickoff against their
    own calendar, which means the invite has to arrive before they accept.
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
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Offer invite test",
            "slug": "cal-offer",
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "Test problem",
            "deliverable_spec": "Test deliverable",
        },
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

    invited = [
        c
        for c in google.calls_of("patch_event_attendees")
        if c.payload["event_id"] == prog.kickoff_event_id
        and any(a.email == "sam-offer@gmail.com" for a in c.payload.get("add") or [])
    ]
    assert invited, "an offered applicant is on the kickoff event before accepting"


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
        json={
            "company_id": company["id"],
            "role_id": str(seeded.id),
            "title": "Idempotent test",
            "slug": "cal-idem",
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "Test",
            "deliverable_spec": "Test",
        },
    ).json()
    programme_id = programme["id"]

    client.post(f"/programmes/{programme_id}/publish")
    assert len(google.calls_of("create_event")) == 1

    # Calling ensure_kickoff_event again should not create a second event
    from projet.services.calendar import ensure_kickoff_event

    prog = session.get(Programme, uuid.UUID(programme_id))
    ensure_kickoff_event(session, prog)
    assert len(google.calls_of("create_event")) == 1
