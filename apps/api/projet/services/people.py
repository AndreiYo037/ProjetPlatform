"""Person resolution — the decision that makes the profile compound.

A returning participant must land on the same Person record, or their profile
starts from nothing on every programme. Matching is on normalised email, and
PRD section 12 question 2 is answered here as "reuse the Person, re-confirm
their details" rather than creating a second record.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from projet.models import Person, normalise_email

NON_GOOGLE_DOMAINS = ("outlook.", "hotmail.", "yahoo.", "proton.", "protonmail.", "icloud.")


def looks_like_email(value: str | None) -> bool:
    """Deliberately permissive.

    A strict validator rejects valid-but-unusual addresses, and FR-204's whole
    stance is to warn rather than block because organisations run Google on
    custom domains. We only reject what cannot be an address at all.
    """
    normalised = normalise_email(value)
    if not normalised or normalised.count("@") != 1:
        return False
    local, _, domain = normalised.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def find_person(
    session: Session, *, contact_email: str, google_email: str | None = None
) -> Person | None:
    contact = normalise_email(contact_email)
    google = normalise_email(google_email)
    # Either address may be used as either field across cohorts: someone applies
    # with their school address one year and their Google address the next, and
    # both have to land on the same Person or the profile restarts.
    clauses = [
        func.lower(Person.contact_email) == contact,
        func.lower(Person.google_email) == contact,
    ]
    if google:
        clauses.append(func.lower(Person.google_email) == google)
        clauses.append(func.lower(Person.contact_email) == google)
    return session.scalar(select(Person).where(or_(*clauses)))


def resolve_person(session: Session, **fields) -> tuple[Person, bool]:
    """Return (person, created). Existing people have their details refreshed —
    a student's course and organisation change between cohorts."""
    contact_email = normalise_email(fields.get("contact_email"))
    if not contact_email:
        raise ValueError("contact_email is required to resolve a person")

    person = find_person(
        session,
        contact_email=contact_email,
        google_email=fields.get("google_email"),
    )
    created = person is None
    if person is None:
        person = Person(contact_email=contact_email, name=fields.get("name", ""))
        session.add(person)

    person.contact_email = contact_email
    for field in (
        "name",
        "phone",
        "organisation",
        "org_type",
        "year_course",
        "job_title",
        "timezone",
    ):
        value = fields.get(field)
        if value:
            setattr(person, field, value)
    google = normalise_email(fields.get("google_email"))
    if google:
        person.google_email = google

    session.flush()
    return person, created


def google_email_warning(email: str | None) -> str | None:
    """FR-204 — warn, never block. Some organisations run Google on a custom
    domain, and a hard block would reject them."""
    normalised = normalise_email(email)
    if not normalised or "@" not in normalised:
        return "That does not look like an email address."
    domain = normalised.split("@", 1)[1]
    if any(domain.startswith(bad) for bad in NON_GOOGLE_DOMAINS):
        return (
            f"{domain} is usually not a Google account. Projet sends Calendar invites "
            "and Meet links to this address, so it needs to be the Google account you "
            "will actually use."
        )
    return None
