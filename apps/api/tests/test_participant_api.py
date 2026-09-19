"""The participant's dashboard over HTTP (FR-500).

FR-1004 and section 8: a participant must never be served a score, a ranking or
a referral flag. That is enforced by the schema having nowhere to put them, and
this is where that gets checked.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import Application, Participant, Programme, ProjectEntry
from projet.models.base import utcnow
from projet.models.enums import (
    ActorType,
    ApplicationStatus,
    AuthorRole,
    ProgrammeStatus,
    ThreadType,
)
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.messaging import open_thread
from projet.services.teams import ensure_submission, ensure_team_for_participant

GOOD_URL = "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz01234567/edit"
OTHER_URL = "https://docs.google.com/spreadsheets/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765432/edit"


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


@pytest.fixture
def signed_in(session, client, participant_factory):
    participant = participant_factory()
    team = ensure_team_for_participant(session, participant)
    ensure_submission(session, team)
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)
    return participant


def test_the_dashboard_answers_what_by_when_and_where(client, signed_in, programme):
    body = client.get("/me/dashboard").json()

    assert body["programme"]["title"] == programme.title
    assert body["programme"]["submit_deadline_at"]
    assert body["programme"]["timezone"]
    assert "kickoff_meet_link" in body["programme"]
    assert body["programme"]["pitch_booking_open"] is True
    assert body["submission"]["status"] == "draft"
    assert {slot["slot"] for slot in body["submission"]["slots"]} == {"artifact", "memo"}
    assert body["active_programmes"][0]["id"] == str(programme.id)
    assert body["past_programmes"] == []


def test_a_participant_can_switch_between_active_programmes(
    client, signed_in, session, programme, company, role
):
    """Several live programmes at once — pick which dashboard to open."""
    other = Programme(
        company_id=company.id,
        role_id=role.id,
        title="Pricing model",
        slug=f"pricing-{uuid.uuid4().hex[:6]}",
        start_at=programme.start_at,
        submit_deadline_at=programme.submit_deadline_at,
        status=ProgrammeStatus.RUNNING,
    )
    session.add(other)
    session.flush()
    application = Application(
        programme_id=other.id,
        person_id=signed_in.person_id,
        consent_share_company=True,
        consent_recording=True,
        consent_captured_at=utcnow(),
        status=ApplicationStatus.ACCEPTED,
    )
    session.add(application)
    session.flush()
    session.add(
        Participant(
            programme_id=other.id,
            person_id=signed_in.person_id,
            application_id=application.id,
        )
    )
    session.flush()

    body = client.get("/me/dashboard").json()
    active_ids = {row["id"] for row in body["active_programmes"]}
    assert active_ids == {str(programme.id), str(other.id)}
    assert body["past_programmes"] == []

    selected = client.get(f"/me/dashboard?programme_id={other.id}").json()
    assert selected["programme"]["id"] == str(other.id)
    assert selected["programme"]["title"] == "Pricing model"


def test_a_programme_moves_to_past_once_its_deadline_passes(
    client, signed_in, session, programme
):
    # No kickoff → past is decided by the submit deadline alone.
    programme.start_at = None
    programme.submit_deadline_at = utcnow() - timedelta(days=1)
    session.flush()

    body = client.get("/me/dashboard").json()
    assert body["active_programmes"] == []
    assert body["past_programmes"][0]["id"] == str(programme.id)
    assert body["programme"]["id"] == str(programme.id)


def test_the_dashboard_never_carries_a_score_or_ranking(client, signed_in):
    """Section 8 — enforced server-side, not by hiding UI."""
    raw = json.dumps(client.get("/me/dashboard").json()).lower()

    for forbidden in ("score", "rank", "would_refer", "referral", "winner"):
        assert forbidden not in raw, f"{forbidden!r} must never reach a participant"


def test_the_dashboard_publishes_the_rubric(client, signed_in, content_dir, session, programme):
    """FR-078 — participants read exactly what they are judged on."""
    from projet.services.rubric import compose_rubric

    compose_rubric(session, programme, content_dir)
    session.flush()

    criteria = client.get("/me/dashboard").json()["criteria"]
    assert [c["slot"] for c in criteria] == [1, 2, 3, 4]
    assert all(c["anchor_5"] for c in criteria)


def test_a_participant_without_a_submission_sees_the_setting_up_state(
    client, session, participant_factory
):
    """FR-506 — a fresh acceptance never sees a half-configured dashboard."""
    participant = participant_factory()
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)

    body = client.get("/me/dashboard").json()
    assert body["provisioning"] is True
    assert body["submission"] is None


def test_pasting_a_link_reports_back_inline(client, signed_in, google):
    response = client.put("/me/submission/link", json={"slot": "artifact", "drive_url": GOOD_URL})
    assert response.status_code == 200
    artifact = next(s for s in response.json()["slots"] if s["slot"] == "artifact")
    assert artifact["access_status"] == "ok"
    assert artifact["filename"]


def test_a_broken_link_keeps_the_submission_incomplete(client, signed_in, google):
    google.stage_denied(GOOD_URL)
    body = client.put(
        "/me/submission/link", json={"slot": "artifact", "drive_url": GOOD_URL}
    ).json()

    assert body["status"] == "draft"
    artifact = next(s for s in body["slots"] if s["slot"] == "artifact")
    assert artifact["access_status"] == "denied"


def test_filling_every_slot_completes_the_submission(client, signed_in, google):
    client.put("/me/submission/link", json={"slot": "artifact", "drive_url": GOOD_URL})
    body = client.put("/me/submission/link", json={"slot": "memo", "drive_url": OTHER_URL}).json()

    assert body["status"] == "complete"
    assert body["submitted_at"]


def test_recheck_picks_up_a_fixed_sharing_setting(client, signed_in, google):
    google.stage_denied(GOOD_URL)
    client.put("/me/submission/link", json={"slot": "artifact", "drive_url": GOOD_URL})
    client.put("/me/submission/link", json={"slot": "memo", "drive_url": OTHER_URL})

    google.drive_files.pop(GOOD_URL)
    body = client.post("/me/submission/recheck").json()
    assert body["status"] == "complete"


def test_the_deadline_refuses_a_late_change(client, signed_in, session, programme, google):
    programme.submit_deadline_at = utcnow() - timedelta(minutes=1)
    session.flush()

    response = client.put("/me/submission/link", json={"slot": "artifact", "drive_url": GOOD_URL})
    assert response.status_code == 409
    assert "locked" in response.json()["detail"]


def test_an_unacknowledged_drop_blocks_on_the_dashboard(client, signed_in, session, programme, rep):
    programme.start_at = utcnow() - timedelta(days=1)
    session.flush()
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Extra dataset",
        body="Just cleared.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )
    session.flush()

    body = client.get("/me/dashboard").json()
    assert [t["id"] for t in body["blocking_acknowledgements"]] == [str(thread.id)]

    client.post(f"/me/threads/{thread.id}/read?acknowledge=true")
    assert client.get("/me/dashboard").json()["blocking_acknowledgements"] == []


def test_the_dashboard_needs_a_participant_session(client):
    client.cookies.clear()
    assert client.get("/me/dashboard").status_code == 401


def test_a_company_user_cannot_use_the_participant_dashboard(client, session, rep):
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=rep.id)
    client.cookies.set(SESSION_COOKIE, raw)
    assert client.get("/me/dashboard").status_code == 403


def test_seeding_a_project_returns_verified_facts_and_a_blank_description(
    client, signed_in, session, programme, company
):
    """POST /me/projects/from-participant — the company and the dates are the
    platform's word; the description is theirs to fill in."""
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)

    response = client.post(f"/me/projects/from-participant/{signed_in.id}")

    assert response.status_code == 201
    body = response.json()
    assert body["verified"] is True
    assert body["title"] == programme.title
    assert body["associated_experience"] == company.name
    assert body["description"] is None
    assert body["artifact_visibility"] == "private"


def test_seeding_before_the_programme_finishes_is_refused(client, signed_in, session, programme):
    # Status COMPLETE with a future deadline is still active — not finished yet.
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()

    response = client.post(f"/me/projects/from-participant/{signed_in.id}")

    assert response.status_code == 400
    assert "not finished" in response.json()["detail"]


def test_you_cannot_seed_a_programme_that_is_not_yours(client, signed_in, session, participant_factory, programme):
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    theirs = participant_factory(name="Someone Else")
    session.flush()

    response = client.post(f"/me/projects/from-participant/{theirs.id}")

    assert response.status_code == 400


def test_the_project_list_carries_no_score(client, signed_in, session, programme):
    """Same section 8 rule as the dashboard: nothing on a participant-facing
    schema has anywhere to put a rating."""
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    client.post(f"/me/projects/from-participant/{signed_in.id}")

    raw = json.dumps(client.get("/me/projects").json()).lower()

    for forbidden in ("score", "rank", "would_refer", "referral"):
        assert forbidden not in raw


def _skill_row(session, name="Rust"):
    from projet.models import Skill
    from projet.models.enums import SkillType

    skill = Skill(name=name, slug=name.lower(), type=SkillType.HARD)
    session.add(skill)
    session.flush()
    return skill


def test_a_participant_can_add_a_self_declared_project(client, signed_in):
    response = client.post(
        "/me/projects",
        json={
            "title": "Weekend build",
            "associated_experience": "Self-organized",
            "description": "Built a bus predictor over a weekend.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["verified"] is False
    assert body["title"] == "Weekend build"
    assert body["description"] == "Built a bus predictor over a weekend."
    assert body["artifact_visibility"] == "private"


def test_a_project_needs_a_title(client, signed_in):
    assert client.post("/me/projects", json={"title": ""}).status_code == 422


def test_editing_a_verified_entry_rewrites_the_description_only(
    client, signed_in, session, programme
):
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    entry_id = client.post(f"/me/projects/from-participant/{signed_in.id}").json()["id"]

    described = client.patch(
        f"/me/projects/{entry_id}", json={"description": "Churn was guessed at."}
    )
    assert described.status_code == 200
    assert described.json()["description"] == "Churn was guessed at."

    facts = client.patch(f"/me/projects/{entry_id}", json={"title": "Something grander"})
    assert facts.status_code == 400
    assert "Cannot change" in facts.json()["detail"]


def test_a_verified_entry_cannot_be_deleted_but_can_be_hidden(
    client, signed_in, session, programme
):
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    entry_id = client.post(f"/me/projects/from-participant/{signed_in.id}").json()["id"]

    assert client.delete(f"/me/projects/{entry_id}").status_code == 400
    assert client.patch(f"/me/projects/{entry_id}", json={"visible": False}).status_code == 200
    # Hidden entries drop out of the owner's own listing too.
    assert client.get("/me/projects").json() == []


def test_a_self_declared_project_can_be_deleted(client, signed_in):
    entry_id = client.post("/me/projects", json={"title": "A thing"}).json()["id"]

    assert client.delete(f"/me/projects/{entry_id}").status_code == 204
    assert client.get("/me/projects").json() == []


def test_links_round_trip_through_the_api(client, signed_in):
    entry_id = client.post("/me/projects", json={"title": "A thing"}).json()["id"]

    added = client.post(
        f"/me/projects/{entry_id}/links",
        json={"url": "https://github.test/repo", "label": "The code"},
    )
    assert added.status_code == 201
    link_id = added.json()["links"][0]["id"]

    removed = client.delete(f"/me/projects/{entry_id}/links/{link_id}")
    assert removed.status_code == 200
    assert removed.json()["links"] == []


def test_a_file_can_be_attached_and_fetched_back(client, signed_in):
    """The stored object is not publicly addressable: the response hands back
    a signed link, and that link is what works."""
    entry_id = client.post("/me/projects", json={"title": "A thing"}).json()["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32

    uploaded = client.post(
        f"/me/projects/{entry_id}/files",
        files={"file": ("shot.png", png, "image/png")},
    )

    assert uploaded.status_code == 201
    link = uploaded.json()["links"][0]
    assert link["filename"] == "shot.png"
    assert link["url"] is None
    assert link["file_url"].startswith("/files/projects/")

    fetched = client.get(link["file_url"])
    assert fetched.status_code == 200
    assert fetched.content == png


def test_an_unsigned_file_url_is_refused(client, signed_in):
    """Stripping the signature off must not work, or the key is the address."""
    entry_id = client.post("/me/projects", json={"title": "A thing"}).json()["id"]
    uploaded = client.post(
        f"/me/projects/{entry_id}/files", files={"file": ("shot.png", b"x" * 16, "image/png")}
    )
    signed = uploaded.json()["links"][0]["file_url"]

    assert client.get(signed.split("?")[0]).status_code in (403, 422)


def test_a_rejected_file_type_is_refused_over_http(client, signed_in):
    entry_id = client.post("/me/projects", json={"title": "A thing"}).json()["id"]

    response = client.post(
        f"/me/projects/{entry_id}/files",
        files={"file": ("run.exe", b"MZ", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "not accepted" in response.json()["detail"]


def test_the_skill_drawer_offers_the_taxonomy_and_tags_a_project(client, signed_in, session):
    skill = _skill_row(session, "Rust")
    entry_id = client.post("/me/projects", json={"title": "Toy"}).json()["id"]

    options = client.get("/me/skills/options").json()
    assert any(option["name"] == "Rust" for option in options)

    tagged = client.put(f"/me/projects/{entry_id}/skills", json={"skill_ids": [str(skill.id)]})
    assert tagged.status_code == 200
    assert [s["name"] for s in tagged.json()["skills"]] == ["Rust"]


def test_a_verified_entry_accepts_an_unverified_skill_over_http(
    client, signed_in, session, programme
):
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    skill = _skill_row(session, "Go")
    entry_id = client.post(f"/me/projects/from-participant/{signed_in.id}").json()["id"]

    response = client.put(f"/me/projects/{entry_id}/skills", json={"skill_ids": [str(skill.id)]})

    assert response.status_code == 200
    assert [s["name"] for s in response.json()["skills"]] == ["Go"]


def test_someone_elses_project_is_a_404(client, signed_in, session, participant_factory):
    stranger = participant_factory(name="Someone Else")
    entry = ProjectEntry(person_id=stranger.person_id, title="Theirs")
    session.add(entry)
    session.flush()

    assert client.patch(f"/me/projects/{entry.id}", json={"title": "Mine"}).status_code == 404
    assert client.delete(f"/me/projects/{entry.id}").status_code == 404
