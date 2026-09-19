"""GET /p/{handle} — FR-1201, reachable with no session.

The one rule this file exists to defend: consent lives in the query, not the
UI. A profile that is off answers 404, a hidden entry never appears in the
JSON, and a private artifact's links never appear even when the entry itself
does.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import Person, ProjectEntry, ProjectLink
from projet.models.enums import ArtifactVisibility, ProgrammeStatus
from projet.services.projects import seed_from_participant


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


def _make_public(session, participant, handle="sam-student"):
    person = session.get(Person, participant.person_id)
    person.handle = handle
    person.public = True
    person.headline = "Data person"
    session.flush()
    return person


def test_an_unknown_handle_is_a_404(client):
    response = client.get("/p/nobody-here")
    assert response.status_code == 404


def test_a_handle_that_exists_but_is_not_public_is_also_a_404(client, session, participant_factory):
    participant = participant_factory()
    person = session.get(Person, participant.person_id)
    person.handle = "still-private"
    person.public = False
    session.flush()

    response = client.get("/p/still-private")
    assert response.status_code == 404


def test_turning_the_profile_off_hides_it_immediately(client, session, participant_factory):
    """Not found for the wrong handle and not found for an off profile look
    identical — otherwise the response itself would leak which handles exist."""
    participant = participant_factory()
    on = _make_public(session, participant, handle="toggle-me")
    assert client.get("/p/toggle-me").status_code == 200

    on.public = False
    session.flush()
    assert client.get("/p/toggle-me").status_code == 404


def test_a_public_profile_carries_no_score_or_ranking(client, session, participant_factory):
    participant = participant_factory()
    _make_public(session, participant)

    import json

    raw = json.dumps(client.get("/p/sam-student").json()).lower()
    for forbidden in ("score", "rank", "would_refer", "referral", "winner"):
        assert forbidden not in raw


def test_verified_and_self_declared_are_counted_apart(client, session, programme, participant_factory):
    from tests._programme_finish import finish_programme

    finish_programme(programme, session)
    participant = participant_factory()
    person = _make_public(session, participant)
    seed_from_participant(session, person.id, participant.id)
    session.add(ProjectEntry(person_id=person.id, title="Weekend build"))
    session.flush()

    body = client.get("/p/sam-student").json()

    assert body["verified_project_count"] == 1
    assert body["self_declared_project_count"] == 1
    assert [p["verified"] for p in body["projects"]] == [True, False]


def test_a_hidden_entry_never_appears(client, session, participant_factory):
    participant = participant_factory()
    person = _make_public(session, participant)
    entry = ProjectEntry(person_id=person.id, title="Not ready", visible=False)
    session.add(entry)
    session.flush()

    body = client.get("/p/sam-student").json()
    assert body["projects"] == []


def test_a_private_artifact_shows_the_entry_but_not_its_links(client, session, participant_factory):
    """The entry's narrative is not the confidential part; its links can be."""
    participant = participant_factory()
    person = _make_public(session, participant)
    entry = ProjectEntry(
        person_id=person.id,
        title="Client dashboard",
        artifact_visibility=ArtifactVisibility.PRIVATE,
    )
    session.add(entry)
    session.flush()
    session.add(ProjectLink(project_entry_id=entry.id, url="https://example.test/demo"))
    session.flush()

    body = client.get("/p/sam-student").json()

    assert body["projects"][0]["title"] == "Client dashboard"
    assert body["projects"][0]["links"] == []


def test_consenting_to_show_links_makes_them_appear(client, session, participant_factory):
    participant = participant_factory()
    person = _make_public(session, participant)
    entry = ProjectEntry(
        person_id=person.id,
        title="Client dashboard",
        artifact_visibility=ArtifactVisibility.PUBLIC,
    )
    session.add(entry)
    session.flush()
    session.add(ProjectLink(project_entry_id=entry.id, url="https://example.test/demo"))
    session.flush()

    body = client.get("/p/sam-student").json()
    assert body["projects"][0]["links"] == [
        {"url": "https://example.test/demo", "filename": None, "label": None}
    ]


def test_an_uploaded_file_is_hidden_and_shown_by_the_same_consent(
    client, session, participant_factory
):
    """A file is the work just as much as a URL is, so one gate covers both."""
    from projet.services.projects import attach_file, create_entry

    participant = participant_factory()
    person = _make_public(session, participant)
    entry = create_entry(session, person.id, title="Client dashboard")
    attach_file(
        session, person.id, entry.id, filename="deck.pdf", content_type="application/pdf", data=b"%PDF-1.4"
    )
    session.flush()

    assert client.get("/p/sam-student").json()["projects"][0]["links"] == []

    entry.artifact_visibility = ArtifactVisibility.PUBLIC
    session.flush()

    link = client.get("/p/sam-student").json()["projects"][0]["links"][0]
    assert link["filename"] == "deck.pdf"
    # Signed even on a public page: the key never becomes a permanent address.
    assert "sig=" in link["url"]
    assert client.get(link["url"]).content == b"%PDF-1.4"
