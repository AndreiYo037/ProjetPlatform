"""FastAPI application.

This slice exposes health and the OpenAPI contract only. Product endpoints land
in Milestone 1; what matters here is that the schema, the outbox and the
scheduler are real and observable.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from projet import __version__
from projet.config import get_settings
from projet.db import get_session
from projet.models import Role
from projet.outbox import worker


def create_app() -> FastAPI:
    app = FastAPI(
        title="Projet API",
        version=__version__,
        description="Proof-of-work hiring infrastructure.",
    )

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz", tags=["ops"])
    def readyz(session: Session = Depends(get_session)) -> dict:
        """Database reachable, taxonomy seeded, outbox not backing up (FR-1304)."""
        checks: dict = {}
        try:
            session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as error:
            checks["database"] = f"error: {error}"
            return {"status": "degraded", "checks": checks}

        roles = len(list(session.scalars(select(Role.id))))
        checks["roles_seeded"] = roles
        checks["outbox"] = worker.health(session)

        healthy = roles > 0 and checks["outbox"]["stuck"] == 0
        return {"status": "ok" if healthy else "degraded", "checks": checks}

    @app.get("/config", tags=["ops"])
    def config() -> dict:
        """Non-secret configuration, so a deploy can be checked at a glance."""
        settings = get_settings()
        return {
            "environment": settings.environment,
            "google_driver": "real" if settings.use_real_google else "fake",
            "database": settings.database_url.split("://", 1)[0],
        }

    return app


app = create_app()
