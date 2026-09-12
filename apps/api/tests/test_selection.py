"""Prescreen, offers and waitlist promotion (FR-300, FR-400).

The acceptance criterion that matters: "a decline at 2am results in the next
person holding an offer before 2:01am."
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from projet.jobs.definitions import expire_offers
from projet.models import Application, Outbox, Submission, Team
from projet.models.base import utcnow
from projet.models.enums import ApplicationStatus
from projet.outbox.application_effects import OFFER_EMAIL
from projet.services.selection import (
    SelectionError,
    accept_offer,
    make_offer,
    promote_from_waitlist,
    reject,
    score_application,
    seat_count,
    waitlist,
)


def _application(session, programme, name="Sam", score=None) -> Application:
    from tests.conftest import make_participant

    participant = make_participant(session, programme, name=name)
    application = session.get(Application, participant.application_id)
    application.status = ApplicationStatus.SUBMITTED
    session.delete(participant)
    session.flush()
    if score is not None:
        application.score_total = score
    session.flush()
    return application


def test_scoring_totals_the_four_criteria(session, programme):
    application = _application(session, programme)
    score_application(
        session, application, relevance=5, specificity=4, capability=3, followthrough=2
    )

    assert application.score_total == 14
    assert application.status == ApplicationStatus.SCREENED


def test_a_score_outside_one_to_five_is_refused(session, programme):
    application = _application(session, programme)
    with pytest.raises(SelectionError, match="between 1 and 5"):
        score_application(session, application, relevance=9)


def test_an_offer_carries_a_token_and_a_48_hour_expiry(session, programme):
    application = _application(session, programme)
    make_offer(session, application)

    assert application.status == ApplicationStatus.OFFERED
    assert application.offer_token
    assert application.offer_expires_at > utcnow() + timedelta(hours=47)

    queued = {row.effect_type for row in session.scalars(select(Outbox))}
    assert OFFER_EMAIL in queued


def test_accepting_creates_the_participant_and_their_team(session, programme, judging_session):
    """FR-402 — acceptance triggers the provisioning chain."""
    application = _application(session, programme)
    make_offer(session, application)
    token = application.offer_token

    participant = accept_offer(session, token)

    assert application.status == ApplicationStatus.ACCEPTED
    assert participant.programme_id == programme.id
    # Team-always, and the submission slots are seeded at acceptance.
    assert session.query(Team).count() == 1
    assert session.query(Submission).count() == 1
    assert participant.judging_session_id == judging_session.id
    assert participant.run_order == 1


def test_an_acceptance_token_is_spent_on_use(session, programme, judging_session):
    """A link that keeps working is a second participant if it is forwarded."""
    application = _application(session, programme)
    make_offer(session, application)
    token = application.offer_token
    accept_offer(session, token)

    with pytest.raises(SelectionError, match="not valid"):
        accept_offer(session, token)


def test_an_expired_offer_cannot_be_accepted(session, programme):
    application = _application(session, programme)
    make_offer(session, application)
    application.offer_expires_at = utcnow() - timedelta(minutes=1)
    session.flush()

    with pytest.raises(SelectionError, match="expired"):
        accept_offer(session, application.offer_token)


def test_seats_count_offers_as_pending(session, programme):
    programme.capacity = 2
    session.flush()
    first = _application(session, programme, name="One")
    make_offer(session, first)

    count = seat_count(session, programme)
    assert count.pending == 1
    assert count.remaining == 1
    assert not count.uncapped


def test_an_uncapped_programme_has_no_remaining_count(session, programme):
    """FR-056a — left null there is no cap, and admin admits by judgement."""
    programme.capacity = None
    session.flush()
    assert seat_count(session, programme).uncapped
    assert seat_count(session, programme).remaining is None


def test_a_released_seat_promotes_the_highest_scoring_waitlisted_applicant(session, programme):
    """FR-404 — the 2am decline."""
    programme.capacity = 1
    programme.start_at = utcnow() + timedelta(days=3)
    session.flush()

    holder = _application(session, programme, name="Holder")
    make_offer(session, holder)

    strong = _application(session, programme, name="Strong", score=18)
    weak = _application(session, programme, name="Weak", score=11)
    waitlist(session, strong)
    waitlist(session, weak)

    assert promote_from_waitlist(session, programme) == []

    holder.status = ApplicationStatus.DECLINED
    holder.offer_token = None
    session.flush()

    promoted = promote_from_waitlist(session, programme)
    assert [a.id for a in promoted] == [strong.id]
    assert strong.status == ApplicationStatus.OFFERED
    assert weak.status == ApplicationStatus.WAITLISTED


def test_an_uncapped_programme_has_no_waitlist_promotion(session, programme):
    """Where capacity is null there is nothing to be waiting for."""
    programme.capacity = None
    session.flush()
    application = _application(session, programme)
    waitlist(session, application)

    assert promote_from_waitlist(session, programme) == []


def test_the_waitlist_closes_at_start_not_at_the_acceptance_deadline(session, programme):
    """FR-405."""
    programme.capacity = 5
    programme.start_at = utcnow() - timedelta(minutes=1)
    session.flush()
    application = _application(session, programme)
    waitlist(session, application)

    assert promote_from_waitlist(session, programme) == []


def test_expiring_an_offer_promotes_the_next_person(session, programme):
    """The job and the promotion are one action: a seat released by expiry must
    not sit unfilled until someone notices."""
    programme.capacity = 1
    programme.start_at = utcnow() + timedelta(days=3)
    session.flush()

    holder = _application(session, programme, name="Holder")
    make_offer(session, holder)
    holder.offer_expires_at = utcnow() - timedelta(minutes=1)

    waiting = _application(session, programme, name="Waiting", score=15)
    waitlist(session, waiting)
    session.flush()

    assert expire_offers(session) == 1
    assert holder.status == ApplicationStatus.EXPIRED
    assert waiting.status == ApplicationStatus.OFFERED


def test_rejection_carries_feedback(session, programme):
    """FR-306 — a one-line feedback field."""
    application = _application(session, programme)
    reject(session, application, "Strong writeup, but the analysis stayed descriptive.")

    assert application.status == ApplicationStatus.REJECTED
    assert "descriptive" in application.rejection_feedback
