"""Testimonials are drafted from endorsed skills and the brief, not invented.

The network call is never made here. What is worth holding is the contract
around it: the prompt carries only facts already on the card, empty replies
are refused, house style is enforced, and a draft does not save or publish.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.claude import (
    DraftingUnavailable,
    build_testimonial_prompt,
    parse_testimonial,
    strip_em_dashes,
)
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import Capability, CompanyUser, PlatformUser, Skill, SkillCapability
from projet.models.enums import ActorType, CompanyUserRole, ProgrammeStatus, SkillType
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.rubric import compose_rubric
from tests.conftest import make_participant
from tests.test_profile_closeout import score_fully, submitted


def drafted(body: str = "I am pleased to recommend Sam Student.") -> str:
    return json.dumps({"body": body})


def test_a_run_returns_the_testimonial_body():
    assert parse_testimonial(drafted("A clear recommendation.")) == "A clear recommendation."


def test_em_dashes_are_removed_rather_than_only_forbidden():
    parsed = parse_testimonial(drafted("Sam showed initiative — and care."))
    assert "—" not in parsed
    assert parsed == "Sam showed initiative - and care."


def test_an_empty_body_is_not_a_testimonial():
    with pytest.raises(DraftingUnavailable) as error:
        parse_testimonial(drafted("  "))
    assert "empty" in str(error.value)


def test_prose_around_the_json_is_tolerated():
    text = "Here you go:\n```json\n" + drafted("Sam was reliable.") + "\n```\n"
    assert parse_testimonial(text) == "Sam was reliable."


def test_a_reply_that_is_not_json_says_so():
    with pytest.raises(DraftingUnavailable) as error:
        parse_testimonial("I could not write this without inventing facts.")
    assert "usable JSON" in str(error.value)


def test_the_prompt_carries_skills_and_the_brief_and_nothing_else():
    prompt = build_testimonial_prompt(
        student_name="Sam Student",
        student_organisation="NUS",
        author_name="Mo Manager",
        author_title="Head of Data",
        company_name="Acme Pte Ltd",
        programme_title="Customer churn dashboard",
        role_name="Data Analytics",
        problem_statement="How can Acme reduce avoidable churn?",
        deliverable_spec="A memo and a dashboard.",
        skill_names=["SQL", "Attention to detail"],
    )
    assert "Sam Student" in prompt
    assert "SQL" in prompt
    assert "Attention to detail" in prompt
    assert "How can Acme reduce avoidable churn?" in prompt
    assert "A memo and a dashboard." in prompt
    assert "NUS" in prompt
    assert "Mo Manager" in prompt
    for leak in ("score", "would_refer", "referral", "total"):
        assert leak not in prompt.lower()


def test_strip_em_dashes_still_keeps_words_apart():
    assert strip_em_dashes("initiative—reliability") == "initiative - reliability"


# -- the endpoint ------------------------------------------------------------


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


@pytest.fixture
def sat(session, programme, content_dir):
    compose_rubric(session, programme, content_dir)
    programme.status = ProgrammeStatus.JUDGING
    sam = make_participant(session, programme, name="Sam Student")
    submitted(session, sam)
    session.flush()
    return {"sam": sam}


def sign_in_company(client, session, user: CompanyUser) -> None:
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=user.id)
    client.cookies.set(SESSION_COOKIE, raw)


def url(programme, participant) -> str:
    return f"/programmes/{programme.id}/participants/{participant.id}/testimonial/draft"


def test_drafting_needs_an_account(client, programme, sat):
    response = client.post(url(programme, sat["sam"]))
    assert response.status_code == 401


def test_platform_staff_do_not_draft_the_company_s_testimonial(client, session, programme, sat):
    admin = PlatformUser(name="Andrei", email="andrei@projet.sg")
    session.add(admin)
    session.flush()
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)

    refused = client.post(url(programme, sat["sam"]))
    assert refused.status_code == 403


def test_drafting_without_a_key_says_so_once_the_facts_are_there(
    client, session, programme, manager, sat, skill
):
    """Without a key the call cannot run, but the guard is what this holds:
    a company reaching drafting is not a 403, and missing facts fail first."""
    programme.problem_statement = "How can Acme reduce avoidable churn?"
    session.flush()
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    response = client.post(url(programme, sat["sam"]))
    assert response.status_code == 503, response.text
    assert "API key" in response.json()["detail"]


def test_drafting_refuses_to_invent_skills(client, session, programme, manager, sat):
    programme.problem_statement = "How can Acme reduce avoidable churn?"
    session.flush()
    sign_in_company(client, session, manager)

    refused = client.post(url(programme, sat["sam"]))
    assert refused.status_code == 422, refused.text
    assert "skills" in refused.json()["detail"].lower()


def test_drafting_refuses_to_invent_a_brief(client, session, programme, manager, sat, skill):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    refused = client.post(url(programme, sat["sam"]))
    assert refused.status_code == 422, refused.text
    assert "problem statement" in refused.json()["detail"].lower()


def test_a_draft_fills_the_box_but_does_not_save(
    client, session, programme, manager, sat, skill, monkeypatch
):
    """Generated wording is not yet the company's word."""
    import projet.integrations.claude as drafting

    programme.problem_statement = "How can Acme reduce avoidable churn?"
    session.flush()
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)

    def fake_draft(**kwargs):
        assert kwargs["skill_names"] == ["SQL"]
        assert "churn" in (kwargs["problem_statement"] or "").lower()
        assert kwargs["student_name"] == "Sam Student"
        return "I am pleased to recommend Sam Student."

    monkeypatch.setattr(drafting, "draft_testimonial", fake_draft)

    created = client.post(url(programme, sat["sam"]))
    assert created.status_code == 200, created.text
    assert created.json()["body"] == "I am pleased to recommend Sam Student."

    from projet.models.profile import Testimonial as TestimonialRow

    assert session.scalars(select(TestimonialRow)).all() == []
    existing = client.get(f"/programmes/{programme.id}/participants/{sat['sam'].id}/testimonial")
    assert existing.json() is None
