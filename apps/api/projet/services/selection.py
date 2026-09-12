"""Prescreen, offers and waitlist promotion (FR-300, FR-400).

The seat logic only applies where capacity is set. Where capacity is null there
is no cap and no waitlist: admin admits as many applicants as they judge worth
admitting (FR-056a).
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projet.models import Application, Participant, Programme
from projet.models.base import utcnow
from projet.models.enums import ApplicationStatus, OutboxSubjectType
from projet.outbox.application_effects import (
    OFFER_EMAIL,
    REJECTION_EMAIL,
    WAITLIST_EMAIL,
)
from projet.outbox.effects import enqueue

OFFER_TTL = timedelta(hours=48)

# FR-079 — the prescreen rubric is admin-only and never published: publishing it
# would teach applicants how to write the application.
PRESCREEN_CRITERIA = ("relevance", "specificity", "capability", "followthrough")

# Statuses that hold a seat: confirmed, or holding a live offer.
SEAT_HOLDING = (ApplicationStatus.OFFERED, ApplicationStatus.ACCEPTED)


class SelectionError(RuntimeError):
    pass


@dataclass
class SeatCount:
    capacity: int | None
    taken: int
    pending: int

    @property
    def uncapped(self) -> bool:
        return self.capacity is None

    @property
    def remaining(self) -> int | None:
        if self.capacity is None:
            return None
        return max(0, self.capacity - self.taken - self.pending)

    @property
    def full(self) -> bool:
        return self.remaining == 0 if self.capacity is not None else False


def seat_count(session: Session, programme: Programme) -> SeatCount:
    taken = session.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.programme_id == programme.id)
        .where(Application.status == ApplicationStatus.ACCEPTED)
    )
    pending = session.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.programme_id == programme.id)
        .where(Application.status == ApplicationStatus.OFFERED)
        .where(Application.offer_expires_at > utcnow())
    )
    return SeatCount(capacity=programme.capacity, taken=taken or 0, pending=pending or 0)


def score_application(
    session: Session, application: Application, **scores: int | None
) -> Application:
    """FR-302 — four criteria at 1-5, total computes live."""
    for key, value in scores.items():
        if key not in PRESCREEN_CRITERIA:
            raise SelectionError(f"unknown prescreen criterion {key!r}")
        if value is not None and not 1 <= value <= 5:
            raise SelectionError(f"{key} must be between 1 and 5")
        setattr(application, f"score_{key}", value)

    parts = [getattr(application, f"score_{c}") for c in PRESCREEN_CRITERIA]
    application.score_total = (
        sum(p for p in parts if p is not None) if any(p is not None for p in parts) else None
    )
    if application.status == ApplicationStatus.SUBMITTED and application.score_total is not None:
        application.status = ApplicationStatus.SCREENED
    session.flush()
    return application


def make_offer(
    session: Session, application: Application, *, base_url_path: str = "/accept"
) -> Application:
    """FR-305 — a unique token with a 48-hour expiry."""
    if application.status in (ApplicationStatus.ACCEPTED, ApplicationStatus.OFFERED):
        raise SelectionError("That applicant already holds an offer.")

    application.offer_token = secrets.token_urlsafe(32)
    application.offer_sent_at = utcnow()
    application.offer_expires_at = utcnow() + OFFER_TTL
    application.status = ApplicationStatus.OFFERED
    session.flush()

    from projet.config import get_settings

    enqueue(
        session,
        subject_type=OutboxSubjectType.APPLICATION,
        subject_id=application.id,
        effect_type=OFFER_EMAIL,
        payload={
            "accept_url": (
                f"{get_settings().app_base_url}{base_url_path}?token={application.offer_token}"
            )
        },
    )
    return application


def waitlist(session: Session, application: Application) -> Application:
    application.status = ApplicationStatus.WAITLISTED
    session.flush()
    enqueue(
        session,
        subject_type=OutboxSubjectType.APPLICATION,
        subject_id=application.id,
        effect_type=WAITLIST_EMAIL,
    )
    return application


def reject(session: Session, application: Application, feedback: str | None = None) -> Application:
    application.status = ApplicationStatus.REJECTED
    application.rejection_feedback = feedback
    session.flush()
    enqueue(
        session,
        subject_type=OutboxSubjectType.APPLICATION,
        subject_id=application.id,
        effect_type=REJECTION_EMAIL,
    )
    return application


def accept_offer(session: Session, token: str) -> Participant:
    """FR-401/402 — accepting triggers the provisioning chain.

    No login required: the token is the authentication, which is what keeps the
    step to one click from an email.
    """
    application = session.scalar(select(Application).where(Application.offer_token == token))
    if application is None:
        raise SelectionError("That acceptance link is not valid.")
    if application.status == ApplicationStatus.ACCEPTED:
        raise SelectionError("You have already accepted this place.")
    if application.status != ApplicationStatus.OFFERED:
        raise SelectionError("That offer is no longer open.")
    if application.offer_expires_at and application.offer_expires_at <= utcnow():
        application.status = ApplicationStatus.EXPIRED
        session.flush()
        raise SelectionError("That offer has expired.")

    programme = session.get(Programme, application.programme_id)
    if programme is None:
        raise SelectionError("That programme no longer exists.")

    application.status = ApplicationStatus.ACCEPTED
    # The token is spent: an acceptance link that keeps working is a second
    # participant if it is forwarded.
    application.offer_token = None

    participant = Participant(
        application_id=application.id,
        programme_id=programme.id,
        person_id=application.person_id,
    )
    session.add(participant)
    session.flush()

    from projet.outbox.provisioning import assign_judging_session, enqueue_provisioning_chain
    from projet.services.teams import ensure_submission, ensure_team_for_participant

    team = ensure_team_for_participant(session, participant)
    ensure_submission(session, team)
    assign_judging_session(session, participant)
    enqueue_provisioning_chain(session, participant)
    session.flush()
    return participant


def promote_from_waitlist(session: Session, programme: Programme) -> list[Application]:
    """FR-404 — on any seat release, the highest-scoring waitlisted applicant is
    promoted and emailed within 60 seconds.

    Only for capacity-set programmes: where capacity is null there is no
    waitlist, because there is nothing to be waiting for.
    """
    if programme.capacity is None:
        return []
    if programme.start_at and utcnow() >= programme.start_at:
        # FR-405 — the waitlist stays live until start_at, not until the
        # acceptance deadline.
        return []

    seats = seat_count(session, programme)
    promoted: list[Application] = []
    remaining = seats.remaining or 0

    if remaining <= 0:
        return []

    candidates = list(
        session.scalars(
            select(Application)
            .where(Application.programme_id == programme.id)
            .where(Application.status == ApplicationStatus.WAITLISTED)
            .order_by(Application.score_total.desc().nullslast(), Application.created_at)
            .limit(remaining)
        )
    )
    for application in candidates:
        make_offer(session, application)
        promoted.append(application)
    session.flush()
    return promoted


def release_seats_and_promote(session: Session, programme_id: uuid.UUID) -> list[Application]:
    programme = session.get(Programme, programme_id)
    if programme is None:
        return []
    return promote_from_waitlist(session, programme)
