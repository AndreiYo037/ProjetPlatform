"""FastAPI application.

Milestone 1: company accounts, programme setup, the public listing, application
intake, the applicant pipeline, and offers with waitlist promotion.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from projet import __version__
from projet.api.applications import router as applications_router
from projet.api.auth import router as auth_router
from projet.api.companies import router as companies_router
from projet.api.programmes import router as programmes_router
from projet.api.public import router as public_router
from projet.api.roles import router as roles_router
from projet.config import get_settings
from projet.db import get_session
from projet.models import Role

# Importing the effect modules registers their handlers. Without this the worker
# has no handler for an effect a route enqueued and marks the row failed, so the
# import is load-bearing rather than incidental.
from projet.outbox import (  # noqa: F401
    application_effects,
    auth_effects,
    provisioning,
    snapshots,
    worker,
)


class OutboxHealth(BaseModel):
    pending: int
    done: int
    failed: int
    stuck: int


class ReadinessChecks(BaseModel):
    database: str
    roles_seeded: int | None = None
    outbox: OutboxHealth | None = None


class Readiness(BaseModel):
    status: str
    checks: ReadinessChecks


class Health(BaseModel):
    status: str
    version: str


class ConfigOut(BaseModel):
    environment: str
    google_driver: str
    database: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="Projet API",
        version=__version__,
        description="Proof-of-work hiring infrastructure.",
    )

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # Sessions are cookie-borne, so the browser must be allowed to send them.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(roles_router)
    app.include_router(programmes_router)
    app.include_router(applications_router)
    app.include_router(public_router)

    @app.get("/files/{key:path}", tags=["files"])
    def serve_file(key: str, sig: str) -> Response:
        """Section 8 — CVs and snapshots are not publicly addressable.

        The signature is scoped to the exact key and expires, so a leaked URL
        stops working and cannot be edited to reach a different file.
        """
        from projet.storage import StorageError, get_storage, verify_signature

        if not verify_signature(key, sig):
            raise HTTPException(403, "That link has expired.")
        try:
            content = get_storage().get(key)
        except StorageError:
            raise HTTPException(404, "Not found.") from None
        media_type = "application/pdf" if key.endswith(".pdf") else "application/octet-stream"
        return Response(content, media_type=media_type)

    @app.get("/healthz", tags=["ops"], response_model=Health)
    def healthz() -> Health:
        return Health(status="ok", version=__version__)

    @app.get("/readyz", tags=["ops"], response_model=Readiness)
    def readyz(session: Session = Depends(get_session)) -> Readiness:
        """Database reachable, taxonomy seeded, outbox not backing up (FR-1304)."""
        try:
            session.execute(text("SELECT 1"))
        except Exception as error:  # noqa: BLE001 - the reason is the useful part
            return Readiness(
                status="degraded",
                checks=ReadinessChecks(database=f"error: {error}"),
            )

        roles = len(list(session.scalars(select(Role.id))))
        counts = worker.health(session)
        healthy = roles > 0 and counts["stuck"] == 0
        return Readiness(
            status="ok" if healthy else "degraded",
            checks=ReadinessChecks(
                database="ok",
                roles_seeded=roles,
                outbox=OutboxHealth(**counts),
            ),
        )

    @app.get("/config", tags=["ops"], response_model=ConfigOut)
    def config() -> ConfigOut:
        """Non-secret configuration, so a deploy can be checked at a glance."""
        return ConfigOut(
            environment=settings.environment,
            google_driver="real" if settings.use_real_google else "fake",
            database=settings.database_url.split("://", 1)[0],
        )

    return app


app = create_app()
