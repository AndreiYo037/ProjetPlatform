"""Closing a programme, and what the participant keeps afterwards.

This is the loop the scoring card opens: a judge tags what they saw and writes a
testimonial, the programme closes, and both become something durable - an
attested skill with a named practitioner behind it, grouped as a credential
under the company and programme that stood behind them.

The rules worth proving are the ones that keep it honest. A credential is not
issued for turning up. A score never reaches the person scored. A draft
testimonial is not a promise. And closing is once.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import (
    Capability,
    CompanyUser,
    Credential,
    Outbox,
    PlatformUser,
    Skill,
    SkillCapability,
    SubmissionLink,
    Testimonial,
)
from projet.models.base import utcnow
from projet.models.enums import (
    AccessStatus,
    ActorType,
    CompanyUserRole,
    ProgrammeStatus,
    SkillType,
)
from projet.outbox.worker import run_once
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.rubric import compose_rubric
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
        title="Head of Data",
        email="mo@acme.test",
        role=CompanyUserRole.OWNER,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def skill(session) -> Skill:
    """A skill that rolls up onto a capability, as the real taxonomy does."""
    skill = Skill(name="SQL", slug="sql", type=SkillType.HARD)
    capability = Capability(
        name="Working with data",
        slug="working-with-data",
        summary="Getting answers out of messy sources.",
        sort_order=1,
    )
    session.add_all([skill, capability])
    session.flush()
    session.add(SkillCapability(skill_id=skill.id, capability_id=capability.id))
    session.flush()
    return skill


def sign_in_company(client, session, user: CompanyUser) -> None:
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=user.id)
    client.cookies.set(SESSION_COOKIE, raw)


def sign_in_participant(client, session, participant) -> None:
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)


def submitted(session, participant):
    team = ensure_team_for_participant(session, participant)
    submission = ensure_submission(session, team)
    for link in session.scalars(
        select(SubmissionLink).where(SubmissionLink.submission_id == submission.id)
    ):
        link.drive_url = "https://docs.google.com/document/d/abc/edit"
        link.detected_filename = "Work"
        link.access_status = AccessStatus.OK
    session.flush()
    return submission


@pytest.fixture
def sat(session, programme, content_dir):
    """A programme at the far end of its week, with two people who presented."""
    compose_rubric(session, programme, content_dir)
    programme.status = ProgrammeStatus.JUDGING
    now = utcnow()
    # Pitch day is the end date, so a past submit_deadline is enough.
    programme.start_at = now - timedelta(days=30)
    programme.submit_deadline_at = now - timedelta(days=1)
    sam = make_participant(session, programme, name="Sam Student")
    ada = make_participant(session, programme, name="Ada Analyst")
    submitted(session, sam)
    submitted(session, ada)
    session.flush()
    return {"sam": sam, "ada": ada}


def score_fully(client, programme, participant, skill=None):
    url = f"/programmes/{programme.id}/participants/{participant.id}/score"
    criteria = client.get(url).json()["criteria"]
    body = {"ratings": {c["criterion_id"]: 4 for c in criteria}}
    if skill is not None:
        body["skill_ids"] = [str(skill.id)]
    response = client.patch(url, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_closing_promotes_the_tags_and_issues_the_credentials(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"], skill)

    closed = client.post(f"/programmes/{programme.id}/close")
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "complete"
    assert body["participants_closed"] == 2
    assert body["credentials_issued"] == 2
    assert body["skills_promoted"] == 2
    assert body["unscored"] == 0


def test_close_emails_when_skills_land_on_a_scored_profile(
    client, session, programme, manager, sat, skill, google
):
    """Close and issue is when the profile becomes real — tell them then."""
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])

    assert client.post(f"/programmes/{programme.id}/close").status_code == 200
    run_once(session, google)

    notes = [
        call
        for call in google.calls_of("send_email")
        if call.payload["subject"] == "Your Projet profile was updated"
    ]
    assert len(notes) == 1
    assert notes[0].payload["to"] == sat["sam"].person.contact_email
    assert programme.title in notes[0].payload["html_body"]
    assert "skill" in notes[0].payload["html_body"]
    assert sat["ada"].person.contact_email not in [call.payload["to"] for call in notes]


def test_a_participant_no_judge_scored_gets_no_credential(
    client, session, programme, manager, sat, skill
):
    """A credential that means attendance is worth nothing to the holder."""
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    body = client.post(f"/programmes/{programme.id}/close").json()
    assert body["participants_closed"] == 1
    assert body["unscored"] == 1

    issued = list(session.scalars(select(Credential.person_id)))
    assert sat["ada"].person_id not in issued
    assert sat["sam"].person_id in issued


def test_a_half_scored_card_does_not_earn_a_credential(
    client, session, programme, manager, sat
):
    """The total is null until all four are rated, and that is the bar."""
    sign_in_company(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{sat['sam'].id}/score"
    criteria = client.get(url).json()["criteria"]
    client.patch(url, json={"ratings": {criteria[0]["criterion_id"]: 5}})

    assert client.post(f"/programmes/{programme.id}/close").json()["credentials_issued"] == 0


def test_closing_twice_is_refused(client, session, programme, manager, sat, skill):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    first = client.post(f"/programmes/{programme.id}/close")
    assert first.status_code == 200
    assert first.json()["credentials_issued"] == 1

    second = client.post(f"/programmes/{programme.id}/close")
    assert second.status_code == 409
    assert "Already closed" in second.json()["detail"]


def test_a_late_score_does_not_reach_the_profile_after_close(
    client, session, programme, manager, sat, skill
):
    """Close is once. A card finished afterwards stays on the card."""
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    assert client.post(f"/programmes/{programme.id}/close").status_code == 200

    score_fully(client, programme, sat["ada"], skill)
    again = client.post(f"/programmes/{programme.id}/close")
    assert again.status_code == 409

    sign_in_participant(client, session, sat["ada"])
    late = client.get("/me/portfolio").json()
    assert late["skills"] == []
    assert late["credentials"] == []

    sign_in_participant(client, session, sat["sam"])
    kept = client.get("/me/portfolio").json()
    assert kept["skills"][0]["name"] == "SQL"
    assert kept["programmes_completed"] == 1


def test_an_open_programme_cannot_close_while_the_week_is_running(
    client, session, programme, manager, sat, skill
):
    programme.status = ProgrammeStatus.OPEN
    programme.start_at = utcnow() + timedelta(days=7)
    programme.submit_deadline_at = utcnow() + timedelta(days=14)
    session.flush()
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    closed = client.post(f"/programmes/{programme.id}/close")
    assert closed.status_code == 409
    assert "still running" in closed.json()["detail"]


def test_a_draft_cannot_close(client, session, programme, manager, sat):
    programme.status = ProgrammeStatus.DRAFT
    session.flush()
    sign_in_company(client, session, manager)
    refused = client.post(f"/programmes/{programme.id}/close")
    assert refused.status_code == 409
    assert "Publish" in refused.json()["detail"]


def test_judge_tags_do_not_reach_the_portfolio_until_close(
    client, session, programme, manager, sat, skill
):
    """The scoring card is a working note. The profile is a claim, and that
    claim is made when the company closes and issues — not when a tag is saved."""
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    sign_in_participant(client, session, sat["sam"])
    body = client.get("/me/portfolio").json()
    assert body["skills"] == []
    assert body["credentials"] == []
    assert body["programmes_completed"] == 0

    sign_in_company(client, session, manager)
    client.post(f"/programmes/{programme.id}/close")

    sign_in_participant(client, session, sat["sam"])
    kept = client.get("/me/portfolio").json()
    assert kept["skills"][0]["name"] == "SQL"
    assert kept["skills"][0]["attesters"] == ["Mo Manager"]
    assert kept["credentials"][0]["skills"] == ["SQL"]
    assert kept["programmes_completed"] == 1


def test_tags_cleared_before_close_never_reach_the_portfolio(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{sat['sam'].id}/score"
    client.patch(url, json={"skill_ids": [str(skill.id)]})
    client.patch(url, json={"skill_ids": []})
    client.post(f"/programmes/{programme.id}/close")

    sign_in_participant(client, session, sat["sam"])
    assert client.get("/me/portfolio").json()["skills"] == []


def test_the_portfolio_shows_attested_skills_with_the_attester(
    client, session, programme, company, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    client.post(f"/programmes/{programme.id}/close")

    sign_in_participant(client, session, sat["sam"])
    portfolio = client.get("/me/portfolio")
    assert portfolio.status_code == 200, portfolio.text
    body = portfolio.json()

    assert body["programmes_completed"] == 1
    cred = body["credentials"][0]
    assert cred["company"] == company.name
    assert cred["programme"] == programme.title
    assert cred["skills"] == ["SQL"]
    assert cred["attesters"] == ["Mo Manager"]
    assert cred["start_at"]
    assert cred["ended_at"]

    # Flat: one row per skill, no capability grouping to make one tag look
    # like two endorsements.
    assert body["skills"][0]["name"] == "SQL"
    # The whole point: a named practitioner, not a self-declaration.
    assert body["skills"][0]["attesters"] == ["Mo Manager"]
    assert body["attester_count"] == 1
    assert body["programme_count"] == 1


def test_the_portfolio_never_carries_a_score(
    client, session, programme, manager, sat, skill
):
    """FR-1004 - the participant sees the evidence, never the arithmetic."""
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    client.post(f"/programmes/{programme.id}/close")

    sign_in_participant(client, session, sat["sam"])
    raw = client.get("/me/portfolio").text.lower()
    for leak in ("total", "criterion", "would_refer", "referral", "score"):
        assert leak not in raw, f"{leak!r} must not reach a participant"


def test_a_testimonial_lands_on_the_profile_at_close(
    client, session, programme, manager, sat
):
    sign_in_company(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial"

    draft = client.put(url, json={"body": "Still thinking about this."})
    assert draft.status_code == 200, draft.text
    assert draft.json()["published_at"] is None

    sign_in_participant(client, session, sat["sam"])
    assert client.get("/me/portfolio").json()["testimonials"] == []

    sign_in_company(client, session, manager)
    empty = client.put(url, json={"body": "   ", "publish": True})
    assert empty.status_code == 422

    published = client.put(url, json={"body": "Sam read the data properly.", "publish": True})
    assert published.status_code == 200, published.text
    assert published.json()["published_at"] is not None
    assert published.json()["pdf_url"]

    sign_in_participant(client, session, sat["sam"])
    assert client.get("/me/portfolio").json()["testimonials"] == []
    notes = list(session.scalars(select(Outbox).where(Outbox.effect_type == "profile_updated_email")))
    assert not any("testimonial" in (row.payload.get("html_body") or "") for row in notes)

    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"])
    assert client.post(f"/programmes/{programme.id}/close").status_code == 200

    sign_in_participant(client, session, sat["sam"])
    kept = client.get("/me/portfolio").json()["testimonials"]
    assert len(kept) == 1
    assert kept[0]["pdf_url"]
    assert kept[0]["author_name"] == "Mo Manager"
    assert kept[0]["author_title"] == "Head of Data"
    assert kept[0]["company"] == "Acme Pte Ltd"
    notes = list(session.scalars(select(Outbox).where(Outbox.effect_type == "profile_updated_email")))
    assert any("testimonial" in (row.payload.get("html_body") or "") for row in notes)


def test_a_text_only_testimonial_does_not_reach_the_profile(
    client, session, programme, manager, sat
):
    """A published row with no generated PDF is treated as unfinished."""
    row = Testimonial(
        participant_id=sat["sam"].id,
        author_company_user_id=manager.id,
        body="Published as text only.",
        published_at=utcnow(),
    )
    session.add(row)
    session.commit()

    sign_in_participant(client, session, sat["sam"])
    assert client.get("/me/portfolio").json()["testimonials"] == []


def test_editing_a_published_testimonial_does_not_unpublish_it(
    client, session, programme, manager, sat
):
    """They may already have put it on a CV; retracting it is not ours to do."""
    sign_in_company(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial"
    first = client.put(url, json={"body": "Good work.", "publish": True}).json()

    edited = client.put(url, json={"body": "Good work, and a clear memo."}).json()
    assert edited["published_at"] == first["published_at"]
    assert edited["body"] == "Good work, and a clear memo."


def test_a_testimonial_is_read_back_as_your_own(
    client, session, programme, company, manager, sat
):
    other = CompanyUser(
        company_id=company.id,
        name="Ren Reviewer",
        email="ren@acme.test",
        role=CompanyUserRole.ADMIN,
    )
    session.add(other)
    session.flush()

    url = f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial"
    sign_in_company(client, session, manager)
    client.put(url, json={"body": "Mo's words."})

    sign_in_company(client, session, other)
    assert client.get(url).json() is None


def test_platform_staff_do_not_write_the_company_s_testimonial(
    client, session, programme, sat
):
    admin = PlatformUser(name="Andrei", email="andrei@projet.sg")
    session.add(admin)
    session.flush()
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)

    refused = client.put(
        f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial",
        json={"body": "Nice."},
    )
    assert refused.status_code == 403


def test_a_participant_cannot_write_their_own_testimonial(client, session, programme, sat):
    sign_in_participant(client, session, sat["sam"])
    refused = client.put(
        f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial",
        json={"body": "I was great."},
    )
    assert refused.status_code in (403, 404)
