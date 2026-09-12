"""Applicant-facing email (section 7.2).

Every one of these is threaded on the person's Gmail thread, so an applicant's
entire correspondence is one conversation rather than nine unrelated messages.
"""

from __future__ import annotations

from projet.models import Application, Company, Participant, Programme
from projet.outbox.effects import EffectContext, PermanentEffectError, effect

APPLICATION_RECEIVED_EMAIL = "application_received_email"
OFFER_EMAIL = "offer_email"
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
        programme.start_at.strftime("%d %B") if programme and programme.start_at else "shortly"
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
    expires = (
        application.offer_expires_at.strftime("%d %B, %H:%M")
        if application.offer_expires_at
        else "48 hours"
    )
    sent = ctx.google.send_email(
        to=application.person.contact_email,
        subject=f"You're in — {programme.title if programme else 'your programme'}",
        html_body=(
            f"<p>Hi {application.person.name},</p>"
            f"<p>{company_name} would like you on this programme.</p>"
            f'<p><a href="{url}">Accept your place</a> — this expires {expires}.</p>'
        ),
        thread_id=_thread_id(ctx, application),
    )
    return {"message_id": sent.message_id}


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
