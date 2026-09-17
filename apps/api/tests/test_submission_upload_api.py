"""The submission upload endpoint over HTTP.

A memo is one static document, so it is submitted by upload rather than a
pasted Drive link — no accessibility probe, no deadline snapshot to wait on.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from projet.db import get_session
from projet.main import create_app
from projet.models.enums import ActorType
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.teams import ensure_submission, ensure_team_for_participant


@pytest.fixture
def client(session, google):
    from projet.integrations.google.client import set_google_client

    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


def sign_in(client, session, participant) -> None:
    _, raw = start_session(session, actor_type=ActorType.PARTICIPANT, subject_id=participant.person_id)
    client.cookies.set(SESSION_COOKIE, raw)


@pytest.fixture
def prepared(session, participant_factory):
    participant = participant_factory()
    team = ensure_team_for_participant(session, participant)
    ensure_submission(session, team)
    session.commit()
    return participant


def test_uploading_a_pdf_fills_the_slot(client, session, prepared):
    sign_in(client, session, prepared)
    response = client.put(
        "/me/submission/upload",
        data={"slot": "memo"},
        files={"file": ("memo.pdf", io.BytesIO(b"%PDF-1.4 memo content"), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    memo = next(s for s in body["slots"] if s["slot"] == "memo")
    assert memo["access_status"] == "ok"
    assert memo["filename"] == "memo.pdf"
    assert memo["file_url"] and "sig=" in memo["file_url"]

    fetched = client.get(memo["file_url"])
    assert fetched.status_code == 200
    assert fetched.content == b"%PDF-1.4 memo content"


def test_a_non_pdf_is_refused(client, session, prepared):
    sign_in(client, session, prepared)
    response = client.put(
        "/me/submission/upload",
        data={"slot": "memo"},
        files={"file": ("memo.docx", io.BytesIO(b"not a pdf"), "application/msword")},
    )
    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]


def test_an_oversized_file_is_refused(client, session, prepared):
    sign_in(client, session, prepared)
    big = b"0" * (20 * 1024 * 1024 + 1)
    response = client.put(
        "/me/submission/upload",
        data={"slot": "memo"},
        files={"file": ("memo.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert response.status_code == 413


def test_removing_an_uploaded_slot_clears_it(client, session, prepared):
    sign_in(client, session, prepared)
    client.put(
        "/me/submission/upload",
        data={"slot": "memo"},
        files={"file": ("memo.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    response = client.delete("/me/submission/link/memo")
    assert response.status_code == 200
    memo = next(s for s in response.json()["slots"] if s["slot"] == "memo")
    assert memo["access_status"] == "unchecked"
    assert memo["file_url"] is None
