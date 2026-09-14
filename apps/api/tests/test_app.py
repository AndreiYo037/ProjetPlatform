"""The API surface this slice actually exposes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from projet.db import get_session
from projet.main import create_app
from projet.seeds.loader import seed_all


def _client(session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_healthz_is_cheap_and_unauthenticated(session):
    response = _client(session).get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_is_degraded_before_the_taxonomy_is_seeded(session):
    body = _client(session).get("/readyz").json()
    assert body["status"] == "degraded"
    assert body["checks"]["roles_seeded"] == 0


def test_readyz_is_ok_once_seeded(session, content_dir):
    seed_all(session, content_dir)
    body = _client(session).get("/readyz").json()

    assert body["status"] == "ok"
    assert body["checks"]["roles_seeded"] == 77
    assert body["checks"]["outbox"] == {"pending": 0, "done": 0, "failed": 0, "stuck": 0}


def test_config_reports_the_google_driver_without_leaking_secrets(session):
    body = _client(session).get("/config").json()
    assert body["google_driver"] == "fake"
    assert "://" not in body["database"]


def test_openapi_schema_is_generated(session):
    body = _client(session).get("/openapi.json").json()
    assert body["info"]["title"] == "Projet API"
    assert "/healthz" in body["paths"]
