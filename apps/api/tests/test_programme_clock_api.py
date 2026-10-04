"""The dates a company picks, over HTTP.

services/schedule.py proves the arithmetic; these tests prove the API pins
times of day and lets any calendar day through.
"""

from __future__ import annotations

import io
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
from tests.conftest import kickoff_on, next_end, next_kickoff, scheduled

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
    payload = {
        "company_id": company_id,
        "role_id": role_id,
        "title": "Churn dashboard",
        "slug": "churn",
        "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        **scheduled(),
        **BRIEF,
    }
    payload.update(overrides)
    # On-site apply opens at start; a pre-start close date is invalid.
    if payload.get("delivery_mode") == "in_person" and "applications_close_at" not in overrides:
        payload["applications_close_at"] = None
    return client.post("/programmes", json=payload)


def test_an_onsite_challenge_keeps_start_and_end_but_no_kickoff(client, company_id, role_id):
    start = next_kickoff()
    end = next_end(start)
    response = create(
        client,
        company_id,
        role_id,
        slug="onsite",
        delivery_mode="in_person",
        start_at=start.isoformat(),
        submit_deadline_at=end.isoformat(),
        kickoff_at=kickoff_on(start).isoformat(),
        pitch_starts_at=None,
        pitch_duration_minutes=None,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["delivery_mode"] == "in_person"
    stored_start = datetime.fromisoformat(body["start_at"]).astimezone(PROGRAMME_TZ)
    stored_end = datetime.fromisoformat(body["submit_deadline_at"]).astimezone(PROGRAMME_TZ)
    assert (stored_start.hour, stored_start.minute) == (
        start.astimezone(PROGRAMME_TZ).hour,
        start.astimezone(PROGRAMME_TZ).minute,
    )
    assert (stored_end.hour, stored_end.minute) == (
        end.astimezone(PROGRAMME_TZ).hour,
        end.astimezone(PROGRAMME_TZ).minute,
    )
    assert body["kickoff_at"] is None
    assert body["pitch_starts_at"] is None

    check = client.get(f"/programmes/{body['id']}/publication-check")
    assert check.status_code == 200, check.text
    assert check.json()["ready"] is True
    assert "kickoff" not in " ".join(check.json()["problems"]).lower()


def test_an_onsite_challenge_cannot_publish_without_start_or_end(client, company_id, role_id):
    created = create(
        client,
        company_id,
        role_id,
        slug="onsite-bare",
        delivery_mode="in_person",
        start_at=None,
        submit_deadline_at=None,
        kickoff_at=None,
        pitch_starts_at=None,
        pitch_duration_minutes=None,
    )
    assert created.status_code == 201, created.text
    check = client.get(f"/programmes/{created.json()['id']}/publication-check").json()
    assert check["ready"] is False
    assert any("start date" in problem for problem in check["problems"])
    assert any("end date" in problem for problem in check["problems"])


def test_an_onsite_challenge_cannot_publish_without_a_brief(client, company_id, role_id):
    start = next_kickoff()
    created = create(
        client,
        company_id,
        role_id,
        slug="onsite-no-brief",
        delivery_mode="in_person",
        start_at=start.isoformat(),
        submit_deadline_at=next_end(start).isoformat(),
        kickoff_at=None,
        pitch_starts_at=None,
        pitch_duration_minutes=None,
        problem_statement=None,
        deliverable_spec=None,
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]
    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is False
    assert any("problem statement" in problem for problem in check["problems"])
    assert any("deliverable" in problem for problem in check["problems"])
    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409


def test_an_onsite_application_before_start_is_refused(client, company_id, role_id):
    start = next_kickoff()
    created = create(
        client,
        company_id,
        role_id,
        slug="onsite-early",
        delivery_mode="in_person",
        start_at=start.isoformat(),
        submit_deadline_at=next_end(start).isoformat(),
        kickoff_at=None,
        pitch_starts_at=None,
        pitch_duration_minutes=None,
    )
    assert created.status_code == 201, created.text
    code = created.json()["apply_access_code"]
    assert code
    programme_id = created.json()["id"]
    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text
    client.cookies.clear()

    refused = client.post(
        "/public/x/acme/onsite-early/apply",
        data={
            "name": "Too Early",
            "contact_email": "early@school.edu.sg",
            "organisation": "NUS",
            "org_type": "school",
            "year_course": "Y2 CS",
            "linkedin_url": "https://www.linkedin.com/in/too-early",
            "access_code": code,
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
        },
    )
    assert refused.status_code == 409
    assert "closed" in refused.json()["detail"].lower()


def test_an_onsite_application_joins_immediately(client, company_id, role_id, session):
    from projet.models import Application, Outbox, Participant, Programme, Submission, Team
    from projet.models.base import utcnow
    from projet.models.enums import ApplicationStatus
    from projet.outbox.application_effects import APPLICATION_RECEIVED_EMAIL

    start = next_kickoff()
    created = create(
        client,
        company_id,
        role_id,
        slug="onsite-apply",
        delivery_mode="in_person",
        start_at=start.isoformat(),
        submit_deadline_at=next_end(start).isoformat(),
        kickoff_at=None,
        pitch_starts_at=None,
        pitch_duration_minutes=None,
    )
    assert created.status_code == 201, created.text
    code = created.json()["apply_access_code"]
    assert code and len(code) == 6
    programme_id = created.json()["id"]
    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text

    import uuid as uuid_mod

    programme = session.get(Programme, uuid_mod.UUID(programme_id))
    assert programme is not None
    programme.start_at = utcnow() - timedelta(minutes=1)
    session.flush()
    client.cookies.clear()

    wrong = client.post(
        "/public/x/acme/onsite-apply/apply",
        data={
            "name": "Wrong Code",
            "contact_email": "wrong@school.edu.sg",
            "organisation": "NUS",
            "org_type": "school",
            "year_course": "Y2 CS",
            "linkedin_url": "https://www.linkedin.com/in/wrong-code",
            "access_code": "NOPE12",
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
        },
    )
    assert wrong.status_code == 403

    listing = client.get("/public/x/acme/onsite-apply").json()
    assert listing["requires_apply_code"] is True
    assert "apply_access_code" not in listing

    applied = client.post(
        "/public/x/acme/onsite-apply/apply",
        data={
            "name": "On Site",
            "contact_email": "onsite@school.edu.sg",
            "organisation": "NUS",
            "org_type": "school",
            "year_course": "Y2 CS",
            "linkedin_url": "https://www.linkedin.com/in/onsite",
            "access_code": code.lower(),
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
        },
    )
    assert applied.status_code == 201, applied.text
    application = session.scalar(select(Application).order_by(Application.created_at.desc()))
    assert application is not None
    assert application.status == ApplicationStatus.ACCEPTED
    participant = session.scalar(
        select(Participant).where(Participant.application_id == application.id)
    )
    assert participant is not None
    assert session.query(Team).count() == 1
    assert session.query(Submission).count() == 1
    queued = {row.effect_type for row in session.scalars(select(Outbox))}
    assert APPLICATION_RECEIVED_EMAIL not in queued

    from projet.models import CompanyUser
    from projet.models.enums import ActorType
    from projet.services.auth import SESSION_COOKIE, start_session

    owner = session.scalar(select(CompanyUser).where(CompanyUser.email == "owner@acme.test"))
    assert owner is not None
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=owner.id)
    client.cookies.set(SESSION_COOKIE, raw)
    refused = client.post(
        f"/programmes/{programme_id}/applications/disposition",
        json={"application_ids": [str(application.id)], "action": "offer"},
    )
    assert refused.status_code == 422
    assert "On-site" in refused.json()["detail"]


def test_an_online_application_still_needs_a_writeup(client, company_id, role_id):
    created = create(client, company_id, role_id, slug="online-apply")
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]
    end = datetime.fromisoformat(created.json()["submit_deadline_at"])
    pitched = client.put(
        f"/programmes/{programme_id}/pitch-schedule",
        json={"starts_at": (end - timedelta(hours=5)).isoformat(), "duration_minutes": 10},
    )
    assert pitched.status_code == 200, pitched.text
    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text
    client.cookies.clear()

    applied = client.post(
        "/public/x/acme/online-apply/apply",
        data={
            "name": "Online",
            "contact_email": "online@school.edu.sg",
            "google_email": "online@gmail.com",
            "availability_confirmed": "true",
            "consent_share_company": "true",
            "consent_recording": "true",
        },
        files={"cv": ("cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert applied.status_code == 422, applied.text


def test_start_and_end_keep_their_clocks(client, company_id, role_id):
    start = datetime(2026, 10, 8, 15, 30, tzinfo=SGT)  # Thursday afternoon
    end = datetime(2026, 10, 25, 18, 0, tzinfo=SGT)
    body = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        submit_deadline_at=end.isoformat(),
        kickoff_at=(start + timedelta(hours=1)).isoformat(),
        pitch_starts_at=(end - timedelta(hours=3)).isoformat(),
        pitch_duration_minutes=10,
        applications_close_at=datetime(2026, 10, 7, tzinfo=SGT).isoformat(),
    ).json()

    stored_start = datetime.fromisoformat(body["start_at"]).astimezone(PROGRAMME_TZ)
    stored_end = datetime.fromisoformat(body["submit_deadline_at"]).astimezone(PROGRAMME_TZ)
    assert stored_start.date() == start.date()
    assert (stored_start.hour, stored_start.minute) == (15, 30)
    assert stored_end.date() == end.date()
    assert (stored_end.hour, stored_end.minute) == (18, 0)
    assert datetime.fromisoformat(body["pitch_at"]) == datetime.fromisoformat(
        body["submit_deadline_at"]
    )


def test_a_thursday_is_as_good_as_any_other_day(client, company_id, role_id):
    thursday = datetime(2026, 10, 8, 9, 0, tzinfo=SGT)
    response = create(
        client,
        company_id,
        role_id,
        applications_close_at=(thursday - timedelta(days=1)).isoformat(),
        **scheduled(thursday),
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
    later_kickoff = later + timedelta(hours=5)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"start_at": later.isoformat(), "kickoff_at": later_kickoff.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["submit_deadline_at"] == original_end
    stored = datetime.fromisoformat(updated.json()["start_at"]).astimezone(PROGRAMME_TZ)
    original = datetime.fromisoformat(programme["start_at"]).astimezone(PROGRAMME_TZ)
    assert (stored.hour, stored.minute) == (original.hour, original.minute)


def test_the_end_date_can_be_set_by_hand(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    pitch = datetime.fromisoformat(programme["pitch_starts_at"])
    new_end = pitch + timedelta(hours=4)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"submit_deadline_at": new_end.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    stored = datetime.fromisoformat(updated.json()["submit_deadline_at"]).astimezone(
        PROGRAMME_TZ
    )
    assert stored.date() == new_end.astimezone(PROGRAMME_TZ).date()
    assert (stored.hour, stored.minute) == (
        new_end.astimezone(PROGRAMME_TZ).hour,
        new_end.astimezone(PROGRAMME_TZ).minute,
    )


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
    assert any("pitching schedule" in problem for problem in check["problems"])
    assert any("problem statement" in problem for problem in check["problems"])
    assert any("deliverable" in problem for problem in check["problems"])

    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409


def test_schedule_and_brief_are_required_to_publish(client, company_id, role_id):
    """Dates, kickoff, pitch, problem statement, and deliverable block publish.
    Applications-close stays a warning. The data pack is optional."""
    start = next_kickoff()
    end = next_end(start)
    created = client.post(
        "/programmes",
        json={
            "company_id": company_id,
            "role_id": role_id,
            "title": "Scheduled without brief",
            "slug": "scheduled-no-brief",
            "start_at": start.isoformat(),
            "submit_deadline_at": end.isoformat(),
            "kickoff_at": kickoff_on(start).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is False
    assert any("pitching schedule" in problem for problem in check["problems"])
    assert any("problem statement" in problem for problem in check["problems"])
    assert any("deliverable" in problem for problem in check["problems"])

    pitched = client.put(
        f"/programmes/{programme_id}/pitch-schedule",
        json={
            "starts_at": (end - timedelta(hours=10)).isoformat(),
            "duration_minutes": 10,
        },
    )
    assert pitched.status_code == 200, pitched.text

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is False
    assert any("problem statement" in problem for problem in check["problems"])
    assert any("deliverable" in problem for problem in check["problems"])
    assert any("closing date" in problem for problem in check["problems"])

    refused = client.post(f"/programmes/{programme_id}/publish")
    assert refused.status_code == 409

    briefed = client.patch(
        f"/programmes/{programme_id}",
        json={
            "problem_statement": BRIEF["problem_statement"],
            "deliverable_spec": BRIEF["deliverable_spec"],
        },
    )
    assert briefed.status_code == 200, briefed.text

    check = client.get(f"/programmes/{programme_id}/publication-check").json()
    assert check["ready"] is True
    assert not any("problem statement" in problem for problem in check["problems"])
    assert not any("deliverable" in problem for problem in check["problems"])
    assert any("closing date" in problem for problem in check["problems"])

    published = client.post(f"/programmes/{programme_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "open"


def test_pitch_must_be_after_start_and_before_end(client, company_id, role_id):
    start = next_kickoff()
    end = next_end(start)
    created = create(
        client,
        company_id,
        role_id,
        slug="pitch-window",
        start_at=start.isoformat(),
        submit_deadline_at=end.isoformat(),
        kickoff_at=kickoff_on(start).isoformat(),
    )
    assert created.status_code == 201, created.text
    programme_id = created.json()["id"]

    too_early = client.put(
        f"/programmes/{programme_id}/pitch-schedule",
        json={"starts_at": start.isoformat(), "duration_minutes": 10},
    )
    assert too_early.status_code == 422

    too_late = client.put(
        f"/programmes/{programme_id}/pitch-schedule",
        json={"starts_at": (end + timedelta(days=1)).isoformat(), "duration_minutes": 10},
    )
    assert too_late.status_code == 422

    ok = client.put(
        f"/programmes/{programme_id}/pitch-schedule",
        json={"starts_at": (end - timedelta(hours=5)).isoformat(), "duration_minutes": 10},
    )
    assert ok.status_code == 200, ok.text


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


def test_kickoff_keeps_its_own_datetime_after_start(client, company_id, role_id):
    start = datetime(2026, 10, 8, 9, 0, tzinfo=SGT)
    picked = datetime(2026, 10, 9, 16, 45, tzinfo=SGT)
    body = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        kickoff_at=picked.isoformat(),
        applications_close_at=datetime(2026, 10, 7, tzinfo=SGT).isoformat(),
    ).json()
    stored = datetime.fromisoformat(body["kickoff_at"]).astimezone(PROGRAMME_TZ)
    assert stored.date() == picked.date()
    assert (stored.hour, stored.minute) == (16, 45)


def test_kickoff_before_start_is_refused(client, company_id, role_id):
    start = datetime(2026, 10, 8, 14, 0, tzinfo=SGT)
    response = create(
        client,
        company_id,
        role_id,
        start_at=start.isoformat(),
        kickoff_at=(start - timedelta(hours=1)).isoformat(),
        applications_close_at=datetime(2026, 10, 7, tzinfo=SGT).isoformat(),
    )
    assert response.status_code == 422
    assert "after the challenge starts" in response.json()["detail"]


def test_moving_the_start_past_kickoff_is_refused(client, company_id, role_id):
    programme = create(client, company_id, role_id).json()
    kickoff = datetime.fromisoformat(programme["kickoff_at"])
    later = kickoff + timedelta(hours=1)

    updated = client.patch(
        f"/programmes/{programme['id']}",
        json={"start_at": later.isoformat()},
    )
    assert updated.status_code == 422
    assert "after the challenge starts" in updated.json()["detail"]
