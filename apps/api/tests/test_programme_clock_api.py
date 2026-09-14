"""The fixed week, over HTTP.

services/schedule.py proves the arithmetic; these tests prove the API refuses
to let a company out of the shape, because that promise is what the apply form
and the pitch invite both rest on.
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
    payload = {
        "company_id": company_id,
        "role_id": role_id,
        "title": "Churn dashboard",
        "slug": "churn",
        "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "start_at": next_kickoff().isoformat(),
        **BRIEF,
    }
    payload.update(overrides)
    return client.post("/programmes", json=payload)


def test_the_deadline_and_pitch_day_follow_from_the_kickoff(client, company_id, role_id):
    kickoff = next_kickoff()
    body = create(client, company_id, role_id, start_at=kickoff.isoformat()).json()

    submit = datetime.fromisoformat(body["submit_deadline_at"])
    pitch = datetime.fromisoformat(body["pitch_at"])
    assert (pitch - kickoff).days == 7
    assert kickoff < submit < pitch


def test_a_kickoff_on_any_other_day_is_refused(client, company_id, role_id):
    thursday = next_kickoff() + timedelta(days=1)
    response = create(client, company_id, role_id, start_at=thursday.isoformat())
    assert response.status_code == 422
    assert "Wednesday" in response.json()["detail"]


def test_applications_cannot_close_after_the_programme_has_begun(client, company_id, role_id):
    kickoff = next_kickoff()
    response = create(
        client,
        company_id,
        role_id,
        applications_close_at=(kickoff + timedelta(days=1)).isoformat(),
    )
    assert response.status_code == 422


def test_a_naive_applications_close_date_from_the_datetime_picker_is_accepted(
    client, company_id, role_id
):
    """The company form's apps-close field is an HTML `datetime-local` input,
    which submits no timezone offset at all — unlike start_at, which comes off
    the kickoff-day picker as a full offset-aware timestamp. The two used to be
    uncomparable and this crashed the whole request with a 500."""
    kickoff = next_kickoff()
    naive_the_day_before = kickoff.replace(tzinfo=None) - timedelta(days=1)
    response = create(
        client,
        company_id,
        role_id,
        start_at=kickoff.isoformat(),
        applications_close_at=naive_the_day_before.isoformat(),
    )
    assert response.status_code == 201, response.text


def test_moving_the_kickoff_moves_the_deadline_with_it(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    later = datetime.fromisoformat(programme["start_at"]) + timedelta(days=7)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"start_at": later.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert datetime.fromisoformat(body["submit_deadline_at"]) > datetime.fromisoformat(
        programme["submit_deadline_at"]
    )
    assert (datetime.fromisoformat(body["pitch_at"]) - later).days == 7


def test_the_submission_deadline_cannot_be_set_by_hand(client, company_id, role_id):
    """It is derived, so an attempt to set it is ignored rather than obeyed."""
    programme = create(client, company_id, role_id).json()
    derived = programme["submit_deadline_at"]

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"submit_deadline_at": (datetime.now(UTC) + timedelta(days=90)).isoformat()},
    )
    assert updated.status_code == 200, updated.text
    assert datetime.fromisoformat(updated.json()["submit_deadline_at"]) == (
        datetime.fromisoformat(derived)
    )


def test_every_programme_is_individual(client, company_id, role_id):
    """Decision: no pairs, no teams. One submission and one verdict per person."""
    programme = create(client, company_id, role_id, team_size_max=4).json()
    assert programme["team_size_max"] == 1


def test_the_offered_kickoff_days_are_all_wednesdays(client, company_id, role_id):
    days = client.get("/programmes/kickoff-days")
    assert days.status_code == 200, days.text
    options = days.json()
    assert options
    for option in options:
        kickoff = datetime.fromisoformat(option["kickoff_at"])
        pitch = datetime.fromisoformat(option["pitch_at"])
        assert kickoff > datetime.now(UTC)
        assert (pitch - kickoff).days == 7


def test_publication_is_blocked_until_the_week_exists(client, company_id, role_id):
    """The kickoff date is the one hard block: nothing else on the clock
    (deadline, pitch day) can be computed without it. The brief is a warning,
    not a refusal — a company can publish a shell to test the pipeline end to
    end and write the brief before a real applicant sees it."""
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
    assert any("kickoff" in problem for problem in check["problems"])
    # Still surfaced as a nudge on the draft page, just not a blocker.
    assert any("problem statement" in problem for problem in check["problems"])

    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409


def test_a_kickoff_alone_is_enough_to_publish(client, company_id, role_id):
    """A company can publish a bare-bones shell to test the flow end to end
    and write the real brief before an applicant ever sees the listing."""
    created = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "Bare but scheduled",
            "slug": "bare-but-scheduled",
            "start_at": next_kickoff().isoformat(),
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
