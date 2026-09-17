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


def test_the_company_announces_to_every_participant(
    client, session, programme, participant_factory, assigned_rep
):
    """FR-601 — one post, the whole cohort, at the same moment."""
    one = participant_factory()
    two = participant_factory()

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    posted = client.post(
        f"/programmes/{programme.id}/threads",
        json={
            "type": "announcement",
            "title": "Pitch order is up",
            "body": "Running order is on your dashboard. Be online ten minutes early.",
        },
    )
    assert posted.status_code == 201, posted.text
    thread_id = posted.json()["thread"]["id"]

    for participant in (one, two):
        sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
        listed = client.get(f"/programmes/{programme.id}/threads").json()
        assert any(t["id"] == thread_id for t in listed)
        thread = client.get(f"/threads/{thread_id}").json()
        assert thread["posts"][0]["author_label"] == "The company"
        assert "Running order" in thread["posts"][0]["body"]


def test_an_announcement_can_require_acknowledgement(
    client, session, programme, participant_factory, assigned_rep
):
    """FR-703 — when the week changes, the company needs to know it landed, so
    the dashboard blocks on it until each participant confirms."""
    participant = participant_factory()

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    thread_id = client.post(
        f"/programmes/{programme.id}/threads",
        json={
            "type": "announcement",
            "title": "Deadline moved",
            "body": "The deadline is now Wednesday.",
            "requires_ack": True,
        },
    ).json()["thread"]["id"]

    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    blocking = client.get("/me/dashboard").json()["blocking_acknowledgements"]
    assert [t["id"] for t in blocking] == [thread_id]

    assert client.post(f"/me/threads/{thread_id}/read?acknowledge=true").status_code == 204
    assert client.get("/me/dashboard").json()["blocking_acknowledgements"] == []


def test_announcements_are_one_continuous_thread(
    client, session, programme, participant_factory, assigned_rep
):
    """No subject to invent: successive posts land in the same thread rather
    than spawning one apiece."""
    participant = participant_factory()
    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)

    first = client.post(
        f"/programmes/{programme.id}/announcements", data={"body": "Data pack is live."}
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"/programmes/{programme.id}/announcements",
        data={"body": "Correction: paid accounts only."},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["title"] is None
    assert [p["body"] for p in second.json()["posts"]] == [
        "Data pack is live.",
        "Correction: paid accounts only.",
    ]

    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    listed = client.get(f"/programmes/{programme.id}/threads").json()
    announcements = [t for t in listed if t["type"] == "announcement"]
    assert len(announcements) == 1
    assert len(announcements[0]["posts"]) == 2


def test_an_announcement_needing_acknowledgement_gets_its_own_thread(
    client, session, programme, participant_factory, assigned_rep
):
    """FR-703 is per-message, so it cannot ride the continuous thread — and
    its title comes from the message, never from a subject field."""
    participant = participant_factory()
    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)

    client.post(f"/programmes/{programme.id}/announcements", data={"body": "Routine notice."})
    acked = client.post(
        f"/programmes/{programme.id}/announcements",
        data={"body": "Deadline moved to Wednesday.\nPitch day unchanged.", "requires_ack": "true"},
    )
    assert acked.status_code == 201
    assert acked.json()["requires_ack"] is True
    assert acked.json()["title"] == "Deadline moved to Wednesday."

    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    blocking = client.get("/me/dashboard").json()["blocking_acknowledgements"]
    assert [t["title"] for t in blocking] == ["Deadline moved to Wednesday."]


def test_a_file_can_be_the_whole_announcement(
    client, session, programme, participant_factory, assigned_rep
):
    import io

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    posted = client.post(
        f"/programmes/{programme.id}/announcements",
        data={"body": ""},
        files={"file": ("churn.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert posted.status_code == 201, posted.text
    post = posted.json()["posts"][-1]
    assert post["body"] == "Attached churn.csv"
    assert [a["filename"] for a in post["attachments"]] == ["churn.csv"]


def test_an_empty_announcement_is_refused(client, session, programme, assigned_rep):
    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    refused = client.post(f"/programmes/{programme.id}/announcements", data={"body": "   "})
    assert refused.status_code == 422
    assert "attach" in refused.json()["detail"].lower()


def test_a_participant_cannot_post_to_announcements(
    client, session, programme, participant_factory
):
    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    refused = client.post(
        f"/programmes/{programme.id}/announcements", data={"body": "Listen up."}
    )
    assert refused.status_code == 403


def test_a_participant_can_attach_a_file_to_their_own_question(
    client, session, programme, participant_factory
):
    """Attachments are not a company privilege — a participant showing the
    error they hit needs to be able to show it."""
    import io

    participant = participant_factory()
    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    thread_id = client.post(
        f"/programmes/{programme.id}/threads",
        json={"type": "question_challenge", "title": "Is this expected?", "body": "See attached."},
    ).json()["thread"]["id"]

    attached = client.post(
        f"/threads/{thread_id}/attachments",
        files={"file": ("error.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    assert attached.status_code == 201, attached.text
    assert [a["filename"] for a in attached.json()["posts"][-1]["attachments"]] == ["error.png"]


def test_a_participant_can_reply_in_the_announcements_thread(
    client, session, programme, participant_factory, assigned_rep
):
    """The company originates the channel; a participant can still speak into
    it once there is something there, the way anyone can reply in a Slack
    channel without being the one who can start a new one."""
    participant = participant_factory()

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    posted = client.post(
        f"/programmes/{programme.id}/announcements", data={"body": "Data pack is live."}
    )
    thread_id = posted.json()["id"]

    sign_in(client, session, ActorType.PARTICIPANT, participant.person_id)
    replied = client.post(f"/threads/{thread_id}/posts", json={"body": "Thanks, got it."})
    assert replied.status_code == 201, replied.text
    assert replied.json()["posts"][-1]["body"] == "Thanks, got it."
    assert replied.json()["posts"][-1]["author_label"] == "A participant"

    sign_in(client, session, ActorType.COMPANY_USER, assigned_rep.id)
    seen = client.get(f"/threads/{thread_id}").json()
    assert seen["posts"][-1]["body"] == "Thanks, got it."
