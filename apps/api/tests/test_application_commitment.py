"""The commitment declared on the form, and the prompt that asks for it.

The company picks the start and end dates. Someone who cannot make them should
find that out on the apply form, before a seat is consumed. So the declaration
is required, and the refusal names both dates rather than saying "missing field".

The writeup prompt is derived from the role's own rubric, so what the form asks
for and what the judge marks stay the same question.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import PlatformUser, Role, RoleTemplate
from projet.models.enums import ActorType
from projet.seeds.loader import seed_all
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.writeup import _first_sentence, derive_writeup_prompt, writeup_prompt_for
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
def role(session, content_dir) -> Role:
    seed_all(session, content_dir)
    return session.scalar(select(Role).where(Role.slug == "data-analytics"))


@pytest.fixture
def listing(client, session, admin, role) -> dict:
    """A published programme, reachable at its public URL."""
    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    company = client.post(
        "/companies",
        json={
            "name": "Acme",
            "slug": "acme",
            "owner_name": "Owner",
            "owner_email": "owner@acme.test",
        },
    ).json()
    programme = client.post(
        "/programmes",
        json={
            "company_id": company["id"],
            "role_id": str(role.id),
            "title": "Churn dashboard",
            "slug": "churn",
            "start_at": next_kickoff().isoformat(),
            "submit_deadline_at": next_end().isoformat(),
            "applications_close_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "problem_statement": "How can Acme cut avoidable churn in its SME tier?",
            "deliverable_spec": "A dashboard with 3-4 views, plus a half-page memo.",
        },
    ).json()
    published = client.post(f"/programmes/{programme['id']}/publish")
    assert published.status_code == 200, published.text
    client.cookies.clear()
    return programme


def application(**overrides) -> dict:
    payload = {
        "name": "Sam Student",
        "contact_email": "sam@school.edu.sg",
        "google_email": "sam@gmail.com",
        "writeup": " ".join(["analysis"] * 220),
        "availability_confirmed": "true",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def apply(client, **overrides):
    return client.post(
        "/public/x/acme/churn/apply",
        data=application(**overrides),
        files={"cv": ("sam.pdf", io.BytesIO(b"%PDF-1.4 cv"), "application/pdf")},
    )


def test_an_application_without_the_declaration_is_refused(client, listing):
    response = apply(client, availability_confirmed=None)
    assert response.status_code == 422
    assert "starts" in response.json()["detail"]


def test_the_refusal_names_both_dates(client, listing):
    """The dates are the reason, so the dates are what the message says."""
    response = apply(client, availability_confirmed="false")
    detail = response.json()["detail"]
    assert "starts on" in detail and "ends on" in detail


def test_the_declaration_is_stored_with_the_application(client, listing, session, admin):
    assert apply(client).status_code == 201

    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    applications = client.get(f"/programmes/{listing['id']}/applications").json()
    detail = client.get(
        f"/programmes/{listing['id']}/applications/{applications[0]['id']}"
    ).json()
    assert detail["availability_confirmed"] is True


def test_a_conflict_during_the_week_is_recorded_without_blocking(client, listing, session, admin):
    """The two fixed dates are the hard part; a Thursday clash is worth knowing."""
    assert apply(client, availability_note="I have an exam on the Friday morning.").status_code == 201

    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    applications = client.get(f"/programmes/{listing['id']}/applications").json()
    detail = client.get(
        f"/programmes/{listing['id']}/applications/{applications[0]['id']}"
    ).json()
    assert "exam" in detail["availability_note"]


def test_a_linkedin_profile_is_kept(client, listing, session, admin):
    assert apply(client, linkedin_url="https://linkedin.com/in/sam").status_code == 201

    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)
    applications = client.get(f"/programmes/{listing['id']}/applications").json()
    detail = client.get(
        f"/programmes/{listing['id']}/applications/{applications[0]['id']}"
    ).json()
    assert detail["linkedin_url"] == "https://linkedin.com/in/sam"


def test_something_that_is_not_a_profile_url_is_refused(client, listing):
    response = apply(client, linkedin_url="sam@school.edu.sg")
    assert response.status_code == 422
    assert "LinkedIn" in response.json()["detail"]


def test_linkedin_is_optional(client, listing):
    assert apply(client, linkedin_url="").status_code == 201


def test_the_listing_carries_the_dates_and_the_prompt(client, listing):
    body = client.get("/public/x/acme/churn").json()
    assert body["start_at"] and body["pitch_at"]
    assert body["writeup_prompt"]
    assert "Data Analytics" in body["writeup_prompt"]
    assert "A dashboard with 3-4 views, plus a half-page memo." in body["writeup_prompt"]


def test_the_prompt_asks_in_the_words_of_the_rubric(session, role, content_dir):
    """Form and scoring card agree because both read the same two slots."""
    template = session.get(RoleTemplate, role.id)
    prompt = derive_writeup_prompt(role, template)
    assert template.rubric_slot2_name.lower() in prompt
    assert template.rubric_slot3_name.lower() in prompt


def test_a_template_can_say_it_in_its_own_words(session, role):
    template = session.get(RoleTemplate, role.id)
    template.writeup_prompt = "  Tell us about one dashboard you regret.  "
    assert writeup_prompt_for(role, template) == "Tell us about one dashboard you regret."


def test_a_role_with_no_template_still_gets_a_prompt(role):
    """Never a blank box: an unseeded role falls back to the generic four asks."""
    prompt = writeup_prompt_for(role, None)
    assert "1." in prompt and "4." in prompt


def test_the_prompt_says_a_job_is_not_required(session, role, content_dir):
    """Most applicants are students. A question that reads as "list your
    professional experience" loses the people this platform exists to reach,
    before anyone has seen what they can do."""
    template = session.get(RoleTemplate, role.id)

    for prompt in (derive_writeup_prompt(role, template), writeup_prompt_for(role, None)):
        assert "does not have to be a job" in prompt
        assert "class project" in prompt


def test_the_deliverable_reads_as_a_sentence(session, role, content_dir):
    """The deliverable is a noun phrase across all 75 roles, so it gets its own
    clause — "approach 4-page PRD" is not English."""
    template = session.get(RoleTemplate, role.id)
    prompt = derive_writeup_prompt(role, template)

    assert "The deliverable this week is:" in prompt
    assert f"approach {template.default_deliverable[:12]}" not in prompt


def test_point_3_uses_the_company_deliverable_not_the_role_default(session, role):
    """Applicants should answer the deliverable the company wrote, not the
    seed default that came with the role."""
    template = session.get(RoleTemplate, role.id)
    company_spec = (
        "- A live deck of three churn views\n"
        "- A half-page memo on which lever to pull first"
    )
    prompt = derive_writeup_prompt(role, template, deliverable=company_spec)

    assert "A live deck of three churn views" in prompt
    assert "which lever to pull first" in prompt
    assert _first_sentence(template.default_deliverable) not in prompt

def test_a_second_application_from_the_same_person_is_refused(client, listing):
    first = apply(client)
    assert first.status_code == 201, first.text
    second = apply(client)
    assert second.status_code == 409
    assert "already applied" in second.json()["detail"].lower()
