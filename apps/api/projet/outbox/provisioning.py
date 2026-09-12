"""The provisioning chain (FR-1400), fired on offer_accepted.

Each step is a separate outbox row. That is the whole point: if step 2 times
out, step 1 is already DONE and will not re-send when the sweep retries.

  1. participant record and submission slots        (in-process, not an effect)
  2. patch kickoff Calendar event with attendee
  3. patch deadline-marker Calendar event
  3a. assign judging session and run-order slot, patch that session's event
  4. welcome email on the person's Gmail thread
  5. increment confirmed count

Steps 2, 3, 3a and 4 are the ones that leave the building, so they are the ones
that live here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from projet.integrations.google.client import Attendee
from projet.models import JudgingSession, Participant, Person, Programme
from projet.outbox.effects import EffectContext, PermanentEffectError, effect

KICKOFF_INVITE = "kickoff_invite"
DEADLINE_MARKER_INVITE = "deadline_marker_invite"
JUDGING_SESSION_INVITE = "judging_session_invite"
WELCOME_EMAIL = "welcome_email"
OFFER_EMAIL = "offer_email"
REJECTION_EMAIL = "rejection_email"
WAITLIST_EMAIL = "waitlist_email"
SESSION_REMOVAL = "judging_session_removal"


def _participant(ctx: EffectContext) -> Participant:
    participant = ctx.session.get(Participant, ctx.row.subject_id)
    if participant is None:
        raise PermanentEffectError(f"participant {ctx.row.subject_id} no longer exists")
    return participant


def _attendee(person: Person) -> Attendee:
    # The Google account, not the contact address: the Calendar invite has to
    # land on an account that can open Meet (FR-204).
    return Attendee(email=person.google_email or person.contact_email, display_name=person.name)


def _patch_named_event(ctx: EffectContext, event_key: str) -> dict:
    event_id = ctx.payload.get(event_key)
    if not event_id:
        raise PermanentEffectError(f"no {event_key} on payload; nothing to patch")
    participant = _participant(ctx)
    ctx.google.patch_event_attendees(event_id, add=[_attendee(participant.person)])
    return {"event_id": event_id}


@effect(KICKOFF_INVITE)
def kickoff_invite(ctx: EffectContext) -> dict:
    return _patch_named_event(ctx, "kickoff_event_id")


@effect(DEADLINE_MARKER_INVITE)
def deadline_marker_invite(ctx: EffectContext) -> dict:
    """The deadline marker carries Calendar's own 24h reminder, which is what
    actually stops a participant missing the deadline — Projet sends nothing."""
    return _patch_named_event(ctx, "deadline_event_id")


@effect(JUDGING_SESSION_INVITE)
def judging_session_invite(ctx: EffectContext) -> dict:
    """FR-811b — the session is assigned at acceptance, so the invite goes out
    now and the day-6 to day-7 gap has no human step in it."""
    participant = _participant(ctx)
    if participant.judging_session_id is None:
        raise PermanentEffectError("participant has no judging session assigned")
    session_row = ctx.session.get(JudgingSession, participant.judging_session_id)
    if session_row is None or not session_row.google_event_id:
        raise PermanentEffectError("judging session has no Calendar event yet")
    ctx.google.patch_event_attendees(
        session_row.google_event_id, add=[_attendee(participant.person)]
    )
    return {"event_id": session_row.google_event_id, "run_order": participant.run_order}


@effect(WELCOME_EMAIL)
def welcome_email(ctx: EffectContext) -> dict:
    participant = _participant(ctx)
    person = participant.person
    programme = ctx.session.get(Programme, participant.programme_id)
    sent = ctx.google.send_email(
        to=person.contact_email,
        subject=f"You're in — {programme.title if programme else 'your programme'}",
        html_body=ctx.payload.get("html_body") or _default_welcome_html(person.name),
        thread_id=participant.gmail_thread_id,
    )
    # Every later touchpoint hangs off this thread (section 7.2).
    participant.gmail_thread_id = sent.thread_id
    return {"message_id": sent.message_id, "thread_id": sent.thread_id}


@effect(SESSION_REMOVAL)
def judging_session_removal(ctx: EffectContext) -> dict:
    """FR-811c — non-submitters come off their session at the deadline and the
    remaining slots close up, with sendUpdates externalOnly so the cohort is
    not re-notified."""
    participant = _participant(ctx)
    event_id = ctx.payload.get("event_id")
    email = ctx.payload.get("email") or participant.person.contact_email
    if not event_id:
        raise PermanentEffectError("no event_id on payload")
    ctx.google.patch_event_attendees(event_id, remove=[email])
    return {"event_id": event_id, "removed": email}


def _default_welcome_html(name: str) -> str:
    return (
        f"<p>Hi {name},</p>"
        "<p>You're confirmed. Your dashboard has the brief, the data pack and your "
        "submission deadline. Calendar invites for kickoff, the deadline and your "
        "judging session are on their way.</p>"
    )


def enqueue_provisioning_chain(
    session,
    participant: Participant,
    *,
    kickoff_event_id: str | None = None,
    deadline_event_id: str | None = None,
) -> list:
    """Queue the whole chain for one acceptance."""
    from projet.models.enums import OutboxSubjectType
    from projet.outbox.effects import enqueue

    rows = []
    if kickoff_event_id:
        rows.append(
            enqueue(
                session,
                subject_type=OutboxSubjectType.PARTICIPANT,
                subject_id=participant.id,
                participant_id=participant.id,
                effect_type=KICKOFF_INVITE,
                payload={"kickoff_event_id": kickoff_event_id},
            )
        )
    if deadline_event_id:
        rows.append(
            enqueue(
                session,
                subject_type=OutboxSubjectType.PARTICIPANT,
                subject_id=participant.id,
                participant_id=participant.id,
                effect_type=DEADLINE_MARKER_INVITE,
                payload={"deadline_event_id": deadline_event_id},
            )
        )
    if participant.judging_session_id:
        rows.append(
            enqueue(
                session,
                subject_type=OutboxSubjectType.PARTICIPANT,
                subject_id=participant.id,
                participant_id=participant.id,
                effect_type=JUDGING_SESSION_INVITE,
            )
        )
    rows.append(
        enqueue(
            session,
            subject_type=OutboxSubjectType.PARTICIPANT,
            subject_id=participant.id,
            participant_id=participant.id,
            effect_type=WELCOME_EMAIL,
        )
    )
    return rows


def assign_judging_session(session, participant: Participant) -> JudgingSession | None:
    """FR-811b/FR-811d — random session, random run order, both at acceptance.

    Run order is generated, not curated: admin can reorder afterwards but
    nothing waits on them.
    """
    sessions = list(
        session.scalars(
            select(JudgingSession)
            .where(JudgingSession.programme_id == participant.programme_id)
            .order_by(JudgingSession.starts_at)
        )
    )
    if not sessions:
        return None

    counts = dict(
        session.execute(
            select(Participant.judging_session_id, func.count())
            .where(Participant.programme_id == participant.programme_id)
            .where(Participant.judging_session_id.is_not(None))
            .group_by(Participant.judging_session_id)
        ).all()
    )
    # Fill the emptiest session first, so sessions stay balanced without admin
    # noticing on the night that one runs to thirty pitches (FR-811b).
    with_room = [s for s in sessions if s.capacity is None or counts.get(s.id, 0) < s.capacity]
    pool = with_room or sessions
    chosen = min(pool, key=lambda s: (counts.get(s.id, 0), s.starts_at))

    participant.judging_session_id = chosen.id
    participant.run_order = counts.get(chosen.id, 0) + 1
    return chosen


def randomise_run_order(session, judging_session_id: uuid.UUID) -> list[Participant]:
    """FR-811d — run order is generated, not curated.

    Acceptance order is arrival order, which correlates with how quickly someone
    checked their email. Shuffling once before the order is published removes
    that, and admin can still reorder by hand afterwards.
    """
    import random

    participants = list(
        session.scalars(
            select(Participant)
            .where(Participant.judging_session_id == judging_session_id)
            .where(Participant.excluded.is_(False))
        )
    )
    random.shuffle(participants)
    for position, participant in enumerate(participants, start=1):
        participant.run_order = position
    return participants
