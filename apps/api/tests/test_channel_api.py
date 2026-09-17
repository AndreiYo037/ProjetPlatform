"""The channel over HTTP, where the visibility guard actually runs.

The service-level tests in test_messaging.py call open_thread and reply
directly, so they never exercise _may_see_thread. That is the layer which
decides whether a participant's direct message reaches the company at all.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.main import create_app
from projet.models import ProgrammeAssignment
from projet.models.enums import ActorType
from projet.services.auth import SESSION_COOKIE, start_session


@pytest.fixture
def client(session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


def sign_in(client, session, actor_type: ActorType, subject_id) -> None:
    client.cookies.clear()
    _, raw = start_session(session, actor_type=actor_type, subject_id=subject_id)
    client.cookies.set(SESSION_COOKIE, raw)


@pytest.fixture
def assigned_rep(session, rep, programme):
    """A rep is scoped to the programmes they are assigned to (FR-015)."""
    session.add(ProgrammeAssignment(programme_id=programme.id, company_user_id=rep.id))
    session.flush()
    return rep


def test_a_direct_message_reaches_the_company(
    client, session, programme, participant_factory, assigned_rep
):
    """FR-605 — a participant writes to the company, and the company can answer.

    Only the author is recorded as a member when a direct thread opens, so a
    membership-based check leaves the company side unable to see it. That is a
    message the participant believes they sent and nobody ever receives.
    """
    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)

    opened = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "direct", "title": "Can I use last year's data?", "body": "Asking privately."},
    )
    assert opened.status_code == 201, opened.text
    thread_id = opened.json()["thread"]["id"]

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    listed = client.get(f"/programmes/{programme.id}/threads")
    assert listed.status_code == 200
    assert any(t["id"] == thread_id for t in listed.json()), (
        "the company cannot see a direct message addressed to it"
    )

    assert client.get(f"/threads/{thread_id}").status_code == 200

    answered = client.post(f"/threads/{thread_id}/posts", json={"body": "Yes, go ahead."})
    assert answered.status_code == 201, answered.text
    assert [p["body"] for p in answered.json()["posts"]][-1] == "Yes, go ahead."


def test_the_participant_sees_the_companys_answer(
    client, session, programme, participant_factory, assigned_rep
):
    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    thread_id = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "direct", "title": "A question", "body": "Privately."},
    ).json()["thread"]["id"]

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    client.post(f"/threads/{thread_id}/posts", json={"body": "Here is the answer."})

    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    thread = client.get(f"/threads/{thread_id}").json()
    assert thread["posts"][-1]["body"] == "Here is the answer."
    assert thread["posts"][-1]["author_label"] == "The company"


def test_a_direct_message_stays_out_of_another_participants_channel(
    client, session, programme, participant_factory, assigned_rep
):
    """The company reading these does not make them public to the cohort."""
    author = participant_factory()
    bystander = participant_factory()

    sign_in(client, session, ActorType.PARTICIPANT, author.person_id)
    thread_id = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "direct", "title": "Mine alone", "body": "Private."},
    ).json()["thread"]["id"]

    sign_in(client, session, ActorType.PARTICIPANT, bystander.person_id)
    listed = client.get(f"/programmes/{programme.id}/threads").json()
    assert all(t["id"] != thread_id for t in listed)
    assert client.get(f"/threads/{thread_id}").status_code == 404


def test_an_unassigned_rep_does_not_see_the_programmes_messages(
    client, session, programme, participant_factory, rep
):
    """FR-015 — programme scoping is what decides this, so an unassigned rep
    is outside it and sees nothing, direct threads included."""
    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    thread_id = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "direct", "title": "Scoped", "body": "Private."},
    ).json()["thread"]["id"]

    sign_in(client, session, ActorType.COMPANY_USER, rep.id)
    assert client.get(f"/programmes/{programme.id}/threads").status_code == 404
    assert client.get(f"/threads/{thread_id}").status_code == 404


def test_a_participant_cannot_post_an_announcement(
    client, session, programme, participant_factory
):
    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    refused = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "announcement", "title": "Listen up", "body": "No."},
    )
    assert refused.status_code == 403
    assert "announcement" in refused.json()["detail"].lower()
