"""Applicant-facing email (section 7.2).

Every one of these is threaded on the person's Gmail thread, so an applicant's
entire correspondence is one conversation rather than nine unrelated messages.
"""

from __future__ import annotations

from projet.models import Application, Company, Participant, Programme
from projet.outbox.effects import EffectContext, PermanentEffectError, effect
from projet.services.schedule import format_sgt_date, format_sgt_datetime

APPLICATION_RECEIVED_EMAIL = "application_received_email"
OFFER_EMAIL = "offer_email"
OFFER_KICKOFF_INVITE = "offer_kickoff_invite"
WAITLIST_EMAIL = "waitlist_email"
REJECTION_EMAIL = "rejection_email"


def _application(ctx: EffectContext) -> Application:
    application = ctx.session.get(Application, ctx.row.subject_id)
    if application is None:
        raise PermanentEffectError(f"application {ctx.row.subject_id} no longer exists")
    return application


def _context(ctx: EffectContext, application: Application) -> tuple[Programme | None, str]:
    programme = ctx.session.get(Programme, application.programme_id)
    company = ctx.session.get(Company, programme.company_id) if programme else None
    return programme, (company.name if company else "the company")


def _thread_id(ctx: EffectContext, application: Application) -> str | None:
    """Reuse the participant's thread where one exists, so later touchpoints
    land in the same conversation."""
    from sqlalchemy import select

    participant = ctx.session.scalar(
        select(Participant).where(Participant.application_id == application.id)
    )
    return participant.gmail_thread_id if participant else None


@effect(APPLICATION_RECEIVED_EMAIL)
def application_received(ctx: EffectContext) -> dict:
    """FR-207 — sends immediately, states the decision date, and opens the
    person's Gmail thread."""
    application = _application(ctx)
    programme, company_name = _context(ctx, application)
    decision_by = (
        format_sgt_date(programme.start_at) if programme and programme.start_at else "shortly"
    )
    sent = ctx.google.send_email(
        to=application.person.contact_email,
        subject=f"We have your application — {programme.title if programme else 'Projet'}",
        html_body=(
            f"<p>Hi {application.person.name},</p>"
            f"<p>Your application to {company_name} is in. We will let you know by "
            f"{decision_by}.</p>"
        ),
    )
    return {"message_id": sent.message_id, "thread_id": sent.thread_id}


@effect(OFFER_EMAIL)
def offer_email(ctx: EffectContext) -> dict:
    """FR-401 — a tokenised acceptance link, no login required."""
    application = _application(ctx)
    programme, company_name = _context(ctx, application)
    url = ctx.payload.get("accept_url")
    if not url:
        raise PermanentEffectError("no acceptance url on payload")
    expires = format_sgt_datetime(application.offer_expires_at) or "48 hours"
    title = programme.title if programme else "your programme"

    kickoff_line = ""
    if programme and programme.start_at:
        starts = format_sgt_datetime(programme.start_at)
        kickoff_line = f"<p><strong>Starts:</strong> {starts}</p>"
        if programme.kickoff_at:
            kickoff_line += (
                f"<p><strong>Kickoff:</strong> {format_sgt_datetime(programme.kickoff_at)}</p>"
            )
        if programme.kickoff_meet_link:
            # The URL is its own visible text: someone joining from a phone, a
            # plain-text client, or a forwarded copy needs the address itself,
            # not link text that survives only as "Join on Google Meet".
            meet = programme.kickoff_meet_link
            kickoff_line += (
                f'<p><strong>Google Meet:</strong> <a href="{meet}">{meet}</a></p>'
            )

    pitch_line = ""
    if programme and programme.pitch_at:
        pitch_line = f"<p><strong>Ends:</strong> {format_sgt_datetime(programme.pitch_at)}</p>"

    sent = ctx.google.send_email(
        to=application.person.contact_email,
        subject=f"You're in — {title}",
        html_body=(
            f"<p>Hi {application.person.name},</p>"
            f"<p>You have been selected for <strong>{title}</strong> with {company_name}.</p>"
            f"{kickoff_line}"
            f"{pitch_line}"
            f'<p><a href="{url}"><strong>Accept your place</strong></a> — '
            f"this expires {expires}.</p>"
        ),
        thread_id=_thread_id(ctx, application),
    )
    return {"message_id": sent.message_id}


@effect(OFFER_KICKOFF_INVITE)
def offer_kickoff_invite(ctx: EffectContext) -> dict:
    """No longer sent. Meet links are in the offer email, not Calendar invites."""
    return {"skipped": True}


@effect(WAITLIST_EMAIL)
def waitlist_email(ctx: EffectContext) -> dict:
    application = _application(ctx)
    programme, company_name = _context(ctx, application)
    sent = ctx.google.send_email(
        to=application.person.contact_email,
        subject=f"You're on the waitlist — {programme.title if programme else 'Projet'}",
        html_body=(
            f"<p>Hi {application.person.name},</p>"
            f"<p>You're on the waitlist for {company_name}. Places do come free, and we "
            "will contact you the moment one does.</p>"
        ),
        thread_id=_thread_id(ctx, application),
    )
    return {"message_id": sent.message_id}


@effect(REJECTION_EMAIL)
def rejection_email(ctx: EffectContext) -> dict:
    """FR-306 — rejections carry a one-line feedback field."""
    application = _application(ctx)
    programme, _ = _context(ctx, application)
    feedback = application.rejection_feedback
    feedback_html = f"<p>{feedback}</p>" if feedback else ""
    sent = ctx.google.send_email(
        to=application.person.contact_email,
        subject=f"Your application — {programme.title if programme else 'Projet'}",
        html_body=(
            f"<p>Hi {application.person.name},</p>"
            "<p>We are not able to offer you a place this time.</p>"
            f"{feedback_html}"
            "<p>We run these regularly and would welcome another application.</p>"
        ),
        thread_id=_thread_id(ctx, application),
    )
    return {"message_id": sent.message_id}
