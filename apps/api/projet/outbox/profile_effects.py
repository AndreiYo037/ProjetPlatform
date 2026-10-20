"""Email when a candidate's profile changes.

Two audiences, one handler: the candidate hears when a company puts something
on their profile, and the company hears when the candidate edits the details
they already shared.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.config import get_settings
from projet.models import Application, Company, CompanyUser, Participant, Person, Programme
from projet.models.enums import CompanyUserStatus, OutboxSubjectType
from projet.outbox.effects import EffectContext, PermanentEffectError, effect, enqueue

PROFILE_UPDATED_EMAIL = "profile_updated_email"
CERTIFICATE_EMAIL = "certificate_email"


@effect(PROFILE_UPDATED_EMAIL)
def profile_updated(ctx: EffectContext) -> dict:
    to = ctx.payload.get("to")
    subject = ctx.payload.get("subject")
    html = ctx.payload.get("html_body")
    if not to or not subject or not html:
        raise PermanentEffectError("profile update email is missing to, subject or body")
    sent = ctx.google.send_email(to=to, subject=subject, html_body=html)
    return {"message_id": sent.message_id, "thread_id": getattr(sent, "thread_id", None)}


@effect(CERTIFICATE_EMAIL)
def certificate_email(ctx: EffectContext) -> dict:
    """The certificate goes out as an attachment.

    The PDF travels inside the payload: the sweep that sends it runs apart
    from the web service and cannot read the web service's stored files.
    """
    import base64

    from projet.integrations.google.client import Attachment

    to = ctx.payload.get("to")
    subject = ctx.payload.get("subject")
    html = ctx.payload.get("html_body")
    data = ctx.payload.get("attachment_b64")
    name = ctx.payload.get("attachment_name") or "certificate.pdf"
    if not to or not subject or not html or not data:
        raise PermanentEffectError("certificate email is missing to, subject, body or file")
    sent = ctx.google.send_email(
        to=to,
        subject=subject,
        html_body=html,
        attachments=[Attachment(filename=name, content=base64.b64decode(data))],
    )
    return {"message_id": sent.message_id, "thread_id": getattr(sent, "thread_id", None)}


def notify_certificate(
    session: Session,
    *,
    person: Person,
    participant_id: uuid.UUID | None,
    subject: str,
    paragraphs: list[str],
    attachment: bytes,
    attachment_name: str,
    key_suffix: str,
    greeting_name: str | None = None,
) -> None:
    """Email a certificate to the person, with the PDF attached."""
    import base64

    if not person.contact_email:
        return
    body = "".join(f"<p>{text}</p>" for text in paragraphs)
    greet = greeting_name or person.name or "there"
    enqueue(
        session,
        subject_type=(
            OutboxSubjectType.PARTICIPANT if participant_id else OutboxSubjectType.APPLICATION
        ),
        subject_id=participant_id or person.id,
        effect_type=CERTIFICATE_EMAIL,
        participant_id=participant_id,
        key_suffix=key_suffix,
        payload={
            "to": person.contact_email,
            "subject": subject,
            "html_body": f"<p>Hi {greet},</p>{body}",
            "attachment_b64": base64.b64encode(attachment).decode(),
            "attachment_name": attachment_name,
        },
    )


def _home_url() -> str:
    return f"{get_settings().app_base_url.rstrip('/')}/home"


def notify_candidate_profile_updated(
    session: Session,
    *,
    person: Person,
    participant_id: uuid.UUID | None,
    what: str,
    key_suffix: str,
    subject: str = "Your Projet profile was updated",
) -> None:
    """The company put something on their profile — tell them."""
    if not person.contact_email:
        return
    enqueue(
        session,
        subject_type=(
            OutboxSubjectType.PARTICIPANT if participant_id else OutboxSubjectType.APPLICATION
        ),
        subject_id=participant_id or person.id,
        effect_type=PROFILE_UPDATED_EMAIL,
        participant_id=participant_id,
        key_suffix=key_suffix,
        payload={
            "to": person.contact_email,
            "subject": subject,
            "html_body": (
                f"<p>Hi {person.name or 'there'},</p>"
                f"<p>{what}</p>"
                f'<p><a href="{_home_url()}">See your profile</a></p>'
            ),
        },
    )


def _watcher_emails(session: Session, person_id: uuid.UUID) -> list[tuple[str, str]]:
    """Company people already looking at this candidate."""
    programme_ids = set(
        session.scalars(select(Application.programme_id).where(Application.person_id == person_id))
    )
    programme_ids.update(
        session.scalars(select(Participant.programme_id).where(Participant.person_id == person_id))
    )
    if not programme_ids:
        return []
    companies = list(
        session.scalars(
            select(Company)
            .join(Programme, Programme.company_id == Company.id)
            .where(Programme.id.in_(programme_ids))
            .distinct()
        )
    )
    seen: set[str] = set()
    recipients: list[tuple[str, str]] = []
    for company in companies:
        users = session.scalars(
            select(CompanyUser)
            .where(CompanyUser.company_id == company.id)
            .where(CompanyUser.status != CompanyUserStatus.DISABLED)
        )
        for user in users:
            email = (user.email or "").strip().lower()
            if email and email not in seen:
                seen.add(email)
                recipients.append((email, company.name))
        contact = (company.contact_email or "").strip().lower()
        if contact and contact not in seen:
            seen.add(contact)
            recipients.append((contact, company.name))
    return recipients


def notify_watchers_candidate_edited(
    session: Session,
    *,
    person: Person,
) -> None:
    """The candidate edited their own details — tell the companies watching."""
    for email, company_name in _watcher_emails(session, person.id):
        enqueue(
            session,
            subject_type=OutboxSubjectType.APPLICATION,
            subject_id=person.id,
            effect_type=PROFILE_UPDATED_EMAIL,
            key_suffix=f"{email}:{uuid.uuid4()}",
            payload={
                "to": email,
                "subject": f"{person.name or 'A candidate'} updated their Projet profile",
                "html_body": (
                    f"<p>{person.name or 'A candidate'} updated the profile they "
                    f"shared with {company_name}.</p>"
                    f"<p>Name: {person.name or '—'}"
                    f"<br>Organisation: {person.organisation or '—'}"
                    f"<br>Year and course: {person.year_course or '—'}"
                    f"<br>Job title: {person.job_title or '—'}</p>"
                ),
            },
        )
