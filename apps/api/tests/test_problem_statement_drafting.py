"""Drafting produces angles a company chooses between, not one take it or leave it.

The network call is never made here. What is worth holding is the contract
around it: how many angles count as a usable run, that exactly five outputs
survive, that the house style is enforced rather than merely requested, and
that a company can run drafting on its own challenge.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from projet.integrations.claude import (
    DraftingUnavailable,
    ProblemStatementDraft,
    parse_angles,
    strip_em_dashes,
)
from projet.models.enums import ActorType
from projet.services.auth import SESSION_COOKIE, start_session


def angle(title: str, outputs: int = 5) -> dict:
    return {
        "title": title,
        "context": "Acme sells payroll software to SMEs in Singapore.",
        "question": "How can Acme reduce avoidable churn in its SME tier?",
        "outputs": [f"Deliverable {i}" for i in range(1, outputs + 1)],
        "grounding": "Their site and a live listing for this role.",
        "based_on_live_listing": True,
    }


def run(*angles: dict) -> str:
    return json.dumps({"angles": list(angles)})


def test_a_run_returns_every_angle_it_drafted():
    parsed = parse_angles(run(angle("Churn"), angle("Onboarding"), angle("Reporting")))
    assert [a.title for a in parsed] == ["Churn", "Onboarding", "Reporting"]


def test_one_angle_is_not_a_choice():
    """A single statement is a yes or a no. The point of the run is the choice."""
    with pytest.raises(DraftingUnavailable) as error:
        parse_angles(run(angle("Churn")))
    assert "at least 2" in str(error.value)


def test_a_fourth_angle_is_dropped():
    parsed = parse_angles(run(*[angle(f"Angle {i}") for i in range(4)]))
    assert len(parsed) == 3


def test_each_angle_carries_exactly_five_outputs():
    parsed = parse_angles(run(angle("Churn", outputs=9), angle("Onboarding", outputs=5)))
    assert [len(a.outputs) for a in parsed] == [5, 5]


def test_em_dashes_are_removed_rather_than_only_forbidden():
    written = angle("Churn")
    written["context"] = "Acme sells payroll software — mostly to SMEs."
    written["outputs"][0] = "A memo — one page"
    parsed = parse_angles(run(written, angle("Onboarding")))
    assert "—" not in parsed[0].context
    assert "—" not in parsed[0].outputs[0]
    assert parsed[0].context == "Acme sells payroll software - mostly to SMEs."


def test_an_angle_missing_its_question_does_not_count():
    broken = angle("Churn")
    broken["question"] = ""
    with pytest.raises(DraftingUnavailable):
        parse_angles(run(broken, angle("Onboarding")))


def test_prose_around_the_json_is_tolerated():
    text = "Here are the angles:\n```json\n" + run(angle("A"), angle("B")) + "\n```\nHope that helps."
    assert len(parse_angles(text)) == 2


def test_a_reply_that_is_not_json_says_so():
    with pytest.raises(DraftingUnavailable) as error:
        parse_angles("I could not find anything about this company.")
    assert "usable JSON" in str(error.value)


def test_strip_em_dashes_keeps_words_apart():
    assert strip_em_dashes("growth—at any cost") == "growth - at any cost"
    assert strip_em_dashes("plain text") == "plain text"


def test_an_angle_renders_in_the_fixed_shape():
    drafted = ProblemStatementDraft(
        title="Churn in the SME tier",
        context="Acme sells payroll software to SMEs.",
        question="How can Acme reduce avoidable churn?",
        outputs=["One", "Two", "Three", "Four", "Five"],
        grounding="Their site.",
        based_on_live_listing=True,
    )
    rendered = drafted.render(2, "Data Analytics")
    lines = rendered.splitlines()
    assert lines[0] == "2. Churn in the SME tier"
    assert lines[1] == "Role fit: Data Analytics"
    assert rendered.count("\n- ") == 5
    assert "—" not in rendered


# -- the endpoint ------------------------------------------------------------


@pytest.fixture
def client(session, google):
    from projet.db import get_session
    from projet.integrations.google.client import set_google_client
    from projet.main import create_app

    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


@pytest.fixture
def owner(session, company):
    from projet.models import CompanyUser
    from projet.models.enums import CompanyUserRole, CompanyUserStatus

    user = CompanyUser(
        company_id=company.id,
        name="Owner",
        email="owner@acme.test",
        role=CompanyUserRole.OWNER,
        status=CompanyUserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    return user


def sign_in(client, session, actor_type, subject_id):
    _, raw = start_session(session, actor_type=actor_type, subject_id=subject_id)
    client.cookies.set(SESSION_COOKIE, raw)


def test_a_company_drafts_on_its_own_challenge(client, session, owner, programme, monkeypatch):
    """Self-serve is the default. Without a key the call cannot run, but the
    guard is what this holds: a company reaching drafting is not a 403."""
    sign_in(client, session, ActorType.COMPANY_USER, owner.id)
    response = client.post(
        f"/programmes/{programme.id}/problem-statement/draft",
        json={"company_url": "https://acme.test"},
    )
    assert response.status_code == 503, response.text
    assert "API key" in response.json()["detail"]


def test_drafting_needs_an_account(client, programme):
    response = client.post(f"/programmes/{programme.id}/problem-statement/draft", json={})
    assert response.status_code == 401


def test_a_run_is_stored_as_a_numbered_batch(client, session, owner, programme, monkeypatch):
    """Three angles from one run share a batch and keep the order offered."""
    import projet.integrations.claude as drafting

    monkeypatch.setattr(
        drafting,
        "draft_problem_statements",
        lambda **_: parse_angles(run(angle("Churn"), angle("Onboarding"), angle("Reporting"))),
    )
    sign_in(client, session, ActorType.COMPANY_USER, owner.id)
    created = client.post(f"/programmes/{programme.id}/problem-statement/draft", json={})
    assert created.status_code == 200, created.text
    body = created.json()

    assert [a["angle"] for a in body] == [1, 2, 3]
    assert len({a["batch_id"] for a in body}) == 1
    assert body[1]["rendered"].startswith("2. Onboarding")

    listed = client.get(f"/programmes/{programme.id}/problem-statement/drafts")
    assert [a["angle"] for a in listed.json()] == [1, 2, 3]
