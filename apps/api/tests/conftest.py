"""Test fixtures.

Tests run on SQLite by default because no Postgres server exists in the build
environment. CI runs the same suite against postgres:16 by setting
PROJET_DATABASE_URL, which is where the production dialect is actually proved.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from projet.config import get_settings
from projet.db import Base
from projet.integrations.google.fake import FakeGoogleClient
from projet.models import (
    Application,
    Company,
    CompanyUser,
    JudgingSession,
    Participant,
    Person,
    Programme,
    Role,
    RoleTemplate,
)
from projet.models.enums import (
    ApplicationStatus,
    CompanyUserRole,
    ProgrammeStatus,
)

CONTENT_DIR = Path(__file__).resolve().parents[3] / "content"


def next_kickoff() -> datetime:
    """A kickoff date a company would actually be offered.

    Every programme starts on a Wednesday (services/schedule.py), so tests must
    pick one the same way the date picker does rather than counting days from
    today and hoping.
    """
    from projet.services.schedule import next_kickoff_days

    # The second offered Wednesday, so "applications close in two days" is
    # always still before kickoff even when today is a Tuesday.
    return next_kickoff_days(datetime.now(UTC), count=2)[1]


@pytest.fixture(scope="session")
def content_dir() -> Path:
    return CONTENT_DIR


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("PROJET_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    kwargs = {}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    engine = create_engine(url, **kwargs)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine) -> Session:
    """Each test runs in a transaction that is rolled back, so tests never see
    each other's rows."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def google() -> FakeGoogleClient:
    return FakeGoogleClient()


@pytest.fixture(autouse=True)
def _settings(tmp_path, monkeypatch):
    """Point storage at a temp dir and force the fake Google driver."""
    get_settings.cache_clear()
    monkeypatch.setenv("PROJET_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("PROJET_GOOGLE_DRIVER", "fake")
    monkeypatch.setenv("PROJET_CONTENT_DIR", str(CONTENT_DIR))
    yield
    get_settings.cache_clear()


# -- object builders ---------------------------------------------------------


@pytest.fixture
def company(session) -> Company:
    company = Company(name="Acme Pte Ltd", slug=f"acme-{uuid.uuid4().hex[:6]}")
    session.add(company)
    session.flush()
    return company


@pytest.fixture
def rep(session, company) -> CompanyUser:
    user = CompanyUser(
        company_id=company.id,
        name="Dana Rep",
        email=f"dana-{uuid.uuid4().hex[:6]}@acme.test",
        role=CompanyUserRole.REP,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def role(session) -> Role:
    """A minimal role with a template, so tests do not depend on a full seed."""
    role = Role(
        name=f"Data Analytics {uuid.uuid4().hex[:4]}",
        slug=f"data-analytics-{uuid.uuid4().hex[:6]}",
        cluster="AI & Data",
        aliases=["data analyst", "BI"],
    )
    session.add(role)
    session.flush()
    session.add(
        RoleTemplate(
            role_id=role.id,
            default_deliverable="Dashboard with 3-4 decision-relevant views",
            public_sources=[{"label": "data.gov.sg", "verification_status": "unverified"}],
            student_tools=["SQL", "Power BI"],
            asks_easy=["their KPI definitions"],
            asks_moderate=["a CSV export with identifiers stripped"],
            asks_hard=["production database access"],
            rubric_slot2_name="Data handling",
            rubric_slot2_anchor_5="Cleaning decisions documented.",
            rubric_slot2_anchor_3="Data prepared correctly.",
            rubric_slot2_anchor_1="Silent row loss.",
            rubric_slot3_name="Insight to decision",
            rubric_slot3_anchor_5="Three findings tied to a decision.",
            rubric_slot3_anchor_3="Real findings, clearly presented.",
            rubric_slot3_anchor_1="Descriptive statistics as insight.",
            ranked_hard_skills=["SQL", "Data cleaning"],
            ranked_soft_skills=["Attention to detail"],
        )
    )
    session.flush()
    return role


@pytest.fixture
def programme(session, company, role) -> Programme:
    now = datetime.now(UTC)
    programme = Programme(
        company_id=company.id,
        role_id=role.id,
        title="Customer churn dashboard",
        slug=f"churn-{uuid.uuid4().hex[:6]}",
        start_at=now,
        submit_deadline_at=now + timedelta(days=6),
        status=ProgrammeStatus.RUNNING,
    )
    session.add(programme)
    session.flush()
    return programme


@pytest.fixture
def judging_session(session, programme) -> JudgingSession:
    row = JudgingSession(
        programme_id=programme.id,
        starts_at=(programme.submit_deadline_at or datetime.now(UTC)) + timedelta(hours=20),
        google_event_id="evt-judging",
        capacity=12,
    )
    session.add(row)
    session.flush()
    return row


def make_participant(
    session,
    programme,
    *,
    name: str = "Sam Student",
    consent_share: bool = True,
    consent_recording: bool = True,
) -> Participant:
    suffix = uuid.uuid4().hex[:8]
    person = Person(
        name=name,
        contact_email=f"{suffix}@school.test",
        google_email=f"{suffix}@gmail.com",
    )
    session.add(person)
    session.flush()
    application = Application(
        programme_id=programme.id,
        person_id=person.id,
        consent_share_company=consent_share,
        consent_recording=consent_recording,
        consent_captured_at=datetime.now(UTC),
        status=ApplicationStatus.ACCEPTED,
    )
    session.add(application)
    session.flush()
    participant = Participant(
        application_id=application.id,
        programme_id=programme.id,
        person_id=person.id,
    )
    session.add(participant)
    session.flush()
    return participant


@pytest.fixture
def participant_factory(session, programme):
    def factory(**kwargs) -> Participant:
        return make_participant(session, programme, **kwargs)

    return factory
