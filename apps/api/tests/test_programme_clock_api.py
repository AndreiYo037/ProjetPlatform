"""The dates a company picks, over HTTP.

services/schedule.py proves the arithmetic; these tests prove the API pins
times of day and lets any calendar day through.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

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
from projet.services.schedule import PROGRAMME_TZ
from tests.conftest import kickoff_on, next_end, next_kickoff

SGT = ZoneInfo("Asia/Singapore")

BRIEF = {
    "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
    "deliverable_spec": "A dashboard with 3-4 views, plus a half-page memo.",
}


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
def role_id(session, content_dir):
    seed_all(session, content_dir)
    return str(session.scalar(select(Role).where(Role.slug == "data-analytics")).id)


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


def create(client, company_id, role_id, **overrides) -> dict:
    start = next_kickoff()
    payload = {
        "company_id": company_id,
        "role_id": role_id,
        "title": "Churn dashboard",
        "slug": "churn",
        "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "start_at": start.isoformat(),
        "submit_deadline_at": next_end(start).isoformat(),
        "kickoff_at": kickoff_on(start).isoformat(),
        **BRIEF,
    }
    payload.update(overrides)
    return client.post("/programmes", json=payload)


def test_start_is_midnight_and_end_is_end_of_day(client, company_id, role_id):
    start = datetime(2026, 10, 8, 15, 30, tzinfo=SGT)  # Thursday afternoon
    end = datetime(2026, 10, 25, 8, 0, tzinfo=SGT)
    body = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        submit_deadline_at=end.isoformat(),
        applications_close_at=datetime(2026, 10, 7, tzinfo=SGT).isoformat(),
    ).json()

    stored_start = datetime.fromisoformat(body["start_at"]).astimezone(PROGRAMME_TZ)
    stored_end = datetime.fromisoformat(body["submit_deadline_at"]).astimezone(PROGRAMME_TZ)
    assert stored_start.date() == start.date()
    assert (stored_start.hour, stored_start.minute) == (0, 0)
    assert stored_end.date() == end.date()
    assert (stored_end.hour, stored_end.minute) == (23, 59)
    assert datetime.fromisoformat(body["pitch_at"]) == datetime.fromisoformat(
        body["submit_deadline_at"]
    )


def test_a_thursday_is_as_good_as_any_other_day(client, company_id, role_id):
    thursday = datetime(2026, 10, 8, tzinfo=SGT)
    response = create(
        client,
        company_id,
        role_id,
        start_at=thursday.isoformat(),
        submit_deadline_at=(thursday + timedelta(days=2)).isoformat(),
        applications_close_at=(thursday - timedelta(days=1)).isoformat(),
    )
    assert response.status_code == 201, response.text


def test_applications_cannot_close_after_the_programme_has_begun(client, company_id, role_id):
    start = next_kickoff()
    response = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        submit_deadline_at=next_end(start).isoformat(),
        applications_close_at=(start + timedelta(days=1)).isoformat(),
    )
    assert response.status_code == 422


def test_a_naive_applications_close_date_from_the_date_picker_is_accepted(
    client, company_id, role_id
):
    start = next_kickoff()
    naive_the_day_before = start.replace(tzinfo=None) - timedelta(days=1)
    response = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        submit_deadline_at=next_end(start).isoformat(),
        applications_close_at=naive_the_day_before.isoformat(),
    )
    assert response.status_code == 201, response.text


def test_moving_the_start_does_not_move_the_end(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    original_end = programme["submit_deadline_at"]
    later = datetime.fromisoformat(programme["start_at"]) + timedelta(days=1)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"start_at": later.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["submit_deadline_at"] == original_end
    stored = datetime.fromisoformat(updated.json()["start_at"]).astimezone(PROGRAMME_TZ)
    assert (stored.hour, stored.minute) == (0, 0)


def test_the_end_date_can_be_set_by_hand(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    new_end = datetime(2026, 12, 1, tzinfo=SGT)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"submit_deadline_at": new_end.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    stored = datetime.fromisoformat(updated.json()["submit_deadline_at"]).astimezone(
        PROGRAMME_TZ
    )
    assert stored.date() == new_end.date()
    assert (stored.hour, stored.minute) == (23, 59)


def test_every_programme_is_individual(client, company_id, role_id):
    """Decision: no pairs, no teams. One submission and one verdict per person."""
    programme = create(client, company_id, role_id, team_size_max=4).json()
    assert programme["team_size_max"] == 1


def test_publication_is_blocked_until_start_end_and_kickoff_exist(client, company_id, role_id):
    bare = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "Bare",
            "slug": "bare",
        },
    )
    assert bare.status_code == 201, bare.text
    programme_id = bare.json()["id"]

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is False
    assert any("start date" in problem for problem in check["problems"])
    assert any("end date" in problem for problem in check["problems"])
    assert any("kickoff time" in problem for problem in check["problems"])
    assert any("problem statement" in problem for problem in check["problems"])

    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409


def test_start_end_and_kickoff_are_enough_to_publish(client, company_id, role_id):
    """A company can publish a bare-bones shell to test the flow end to end
    and write the real brief before an applicant ever sees the listing."""
    start = next_kickoff()
    created = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "Bare but scheduled",
            "slug": "bare-but-scheduled",
            "start_at": start.isoformat(),
            "submit_deadline_at": next_end(start).isoformat(),
            "kickoff_at": kickoff_on(start).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is True
    assert any("problem statement" in problem for problem in check["problems"])
    assert any("closing date" in problem for problem in check["problems"])

    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "open"


def test_dates_without_a_kickoff_time_cannot_publish(client, company_id, role_id):
    start = next_kickoff()
    created = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "No kickoff yet",
            "slug": "no-kickoff-yet",
            "start_at": start.isoformat(),
            "submit_deadline_at": next_end(start).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]
    assert created.json()["kickoff_at"] is None

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is False
    assert any("kickoff time" in problem for problem in check["problems"])

    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409


def test_kickoff_is_the_picked_time_on_the_start_date(client, company_id, role_id):
    start = datetime(2026, 10, 8, tzinfo=SGT)
    picked = datetime(2026, 10, 1, 16, 45, tzinfo=SGT)
    body = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        kickoff_at=picked.isoformat(),
        applications_close_at=datetime(2026, 10, 7, tzinfo=SGT).isoformat(),
    ).json()
    stored = datetime.fromisoformat(body["kickoff_at"]).astimezone(PROGRAMME_TZ)
    assert stored.date() == start.date()
    assert (stored.hour, stored.minute) == (16, 45)


def test_moving_the_start_keeps_the_kickoff_clock(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    original = datetime.fromisoformat(programme["kickoff_at"]).astimezone(PROGRAMME_TZ)
    later = datetime.fromisoformat(programme["start_at"]) + timedelta(days=1)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"start_at": later.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    stored = datetime.fromisoformat(updated.json()["kickoff_at"]).astimezone(PROGRAMME_TZ)
    assert stored.date() == later.astimezone(PROGRAMME_TZ).date()
    assert (stored.hour, stored.minute) == (original.hour, original.minute)
