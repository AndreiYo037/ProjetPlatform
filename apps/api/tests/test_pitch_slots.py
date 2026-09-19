"""Company sets the pitching clock; participants claim slots first-come-first-served.

How many slots exist is how many submissions have been handed in.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import CompanyUser, SubmissionLink
from projet.models.enums import AccessStatus, ActorType, CompanyUserRole
from projet.outbox.worker import run_once
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.submission import _refresh_status
from projet.services.teams import ensure_submission, ensure_team_for_participant
from tests.conftest import make_participant


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


def sign_in_participant(client, session, participant) -> None:
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)


def hand_in(session, participant):
    """A complete submission: that is what opens a timeslot."""
    team = ensure_team_for_participant(session, participant)
    submission = ensure_submission(session, team)
    for link in session.scalars(
        select(SubmissionLink).where(SubmissionLink.submission_id == submission.id)
    ):
        link.drive_url = "https://example.com/work"
        link.access_status = AccessStatus.OK
    _refresh_status(session, submission)
    session.flush()
    return submission


def set_clock(client, programme, *, slots_minutes=10):
    starts = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
    response = client.put(
        f"/programmes/{programme.id}/pitch-schedule",
        json={"starts_at": starts.isoformat(), "duration_minutes": slots_minutes},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_the_clock_opens_one_slot_per_submission(
    client, session, programme, manager, google
):
    sign_in_company(client, session, manager)
    for name in ("Sam", "Ada", "Lin"):
        hand_in(session, make_participant(session, programme, name=name))

    payload = set_clock(client, programme)
    assert payload["duration_minutes"] == 10
    assert payload["meet_link"]
    assert len(payload["slots"]) == 3
    assert not any(slot["taken"] for slot in payload["slots"])
    assert google.calls_of("create_event")


def test_no_submissions_means_no_slots(client, session, programme, manager):
    sign_in_company(client, session, manager)
    payload = set_clock(client, programme)
    assert payload["slots"] == []


def test_a_later_submission_opens_another_slot(client, session, programme, manager):
    sign_in_company(client, session, manager)
    hand_in(session, make_participant(session, programme, name="Sam"))
    assert len(set_clock(client, programme)["slots"]) == 1

    hand_in(session, make_participant(session, programme, name="Ada"))
    listed = client.get(f"/programmes/{programme.id}/pitch-schedule").json()
    assert len(listed["slots"]) == 2


def test_the_first_claim_gets_the_slot_without_emailing(
    client, session, programme, manager, google
):
    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    hand_in(session, sam)
    hand_in(session, ada)
    sign_in_company(client, session, manager)
    slots = set_clock(client, programme)["slots"]
    first, second = slots[0]["id"], slots[1]["id"]

    sign_in_participant(client, session, sam)
    booked = client.post("/me/pitch-slot", json={"session_id": first})
    assert booked.status_code == 200, booked.text
    dash = booked.json()
    assert dash["judging"]["id"] == first
    assert dash["judging"]["location_or_meet_link"]
    assert {slot["id"] for slot in dash["pitch_slots"] if not slot["available"]} == {first}

    run_once(session, google)
    assert google.calls_of("send_email") == []

    sign_in_participant(client, session, ada)
    refused = client.post("/me/pitch-slot", json={"session_id": first})
    assert refused.status_code == 409
    taken = client.post("/me/pitch-slot", json={"session_id": second})
    assert taken.status_code == 200, taken.text
    assert taken.json()["judging"]["id"] == second


def test_you_cannot_claim_a_slot_before_you_submit(
    client, session, programme, manager
):
    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    hand_in(session, ada)
    sign_in_company(client, session, manager)
    slot_id = set_clock(client, programme)["slots"][0]["id"]

    sign_in_participant(client, session, sam)
    refused = client.post("/me/pitch-slot", json={"session_id": slot_id})
    assert refused.status_code == 422
    assert "Submit" in refused.json()["detail"]


def test_judging_cards_sort_by_booked_slot_and_carry_the_meet(
    client, session, programme, manager
):
    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    hand_in(session, sam)
    hand_in(session, ada)
    sign_in_company(client, session, manager)
    slots = set_clock(client, programme)["slots"]

    sign_in_participant(client, session, sam)
    client.post("/me/pitch-slot", json={"session_id": slots[1]["id"]})
    sign_in_participant(client, session, ada)
    client.post("/me/pitch-slot", json={"session_id": slots[0]["id"]})

    sign_in_company(client, session, manager)
    cards = client.get(f"/programmes/{programme.id}/submissions").json()
    assert [card["name"] for card in cards] == ["Ada Analyst", "Sam Student"]
    assert cards[0]["meet_link"]
    assert cards[0]["pitch_at"]
    score = client.get(
        f"/programmes/{programme.id}/participants/{ada.id}/score"
    ).json()
    assert score["submission"]["meet_link"] == cards[0]["meet_link"]


def test_pickable_slots_are_not_auto_assigned_at_acceptance(
    client, session, programme, manager
):
    sign_in_company(client, session, manager)
    set_clock(client, programme)
    sam = make_participant(session, programme, name="Sam Student")
    from projet.outbox.provisioning import assign_judging_session

    assert assign_judging_session(session, sam) is None
    assert sam.judging_session_id is None
    sign_in_participant(client, session, sam)
    body = client.get("/me/dashboard").json()
    assert body["judging"] is None
    assert body["pitch_slots"] == []

    hand_in(session, sam)
    after = client.get("/me/dashboard").json()
    assert after["judging"] is None
    assert len(after["pitch_slots"]) == 1
    assert after["pitch_slots"][0]["available"] is True


def test_a_slot_can_be_changed_before_judging_day(
    client, session, programme, manager
):
    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    hand_in(session, sam)
    hand_in(session, ada)
    sign_in_company(client, session, manager)
    first, second = [slot["id"] for slot in set_clock(client, programme)["slots"]]

    sign_in_participant(client, session, sam)
    assert client.post("/me/pitch-slot", json={"session_id": first}).status_code == 200
    changed = client.post("/me/pitch-slot", json={"session_id": second})
    assert changed.status_code == 200, changed.text
    assert changed.json()["judging"]["id"] == second


def test_a_slot_cannot_be_changed_on_judging_day(
    client, session, programme, manager
):
    """Lock is 00:00 SGT that day, even if the first pitch is still hours away."""
    from projet.services.schedule import PROGRAMME_TZ, in_programme_tz

    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    hand_in(session, sam)
    hand_in(session, ada)
    sign_in_company(client, session, manager)
    first, second = [slot["id"] for slot in set_clock(client, programme)["slots"]]

    sign_in_participant(client, session, sam)
    assert client.post("/me/pitch-slot", json={"session_id": first}).status_code == 200

    today = in_programme_tz(datetime.now(UTC)).date()
    programme.pitch_starts_at = datetime(today.year, today.month, today.day, 23, 59, tzinfo=PROGRAMME_TZ)
    session.flush()

    refused = client.post("/me/pitch-slot", json={"session_id": second})
    assert refused.status_code == 409
    assert "cannot change" in refused.json()["detail"].lower()
    dash = client.get("/me/dashboard").json()
    assert dash["judging"]["id"] == first
    assert dash["programme"]["pitch_booking_open"] is False
