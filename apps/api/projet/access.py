"""Consent enforcement and audience separation.

Section 8: "Consent enforced at the query layer, not the UI. Non-consenting
participants cannot appear in any export by construction."

Every company-facing read of applicant or participant data goes through this
module. A route that builds its own select() over Application or Participant is
a bug, and test_consent.py is what catches it.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select

from projet.models import Application, Participant, Person, Submission, Team, TeamMember


def company_visible_applications(programme_id: uuid.UUID) -> Select:
    """Applications a company may see: those that consented to sharing (FR-020)."""
    return (
        select(Application)
        .where(Application.programme_id == programme_id)
        .where(Application.consent_share_company.is_(True))
    )


def company_visible_participants(programme_id: uuid.UUID) -> Select:
    """Participants a company may see, joined through the consent on their
    application. Consent lives on the Application because that is where it was
    captured and timestamped; the Participant inherits it rather than copying it,
    so a withdrawal has one place to take effect (FR-021)."""
    return (
        select(Participant)
        .join(Application, Participant.application_id == Application.id)
        .where(Participant.programme_id == programme_id)
        .where(Application.consent_share_company.is_(True))
    )


def company_candidate_pool(company_id: uuid.UUID) -> Select:
    """FR-017/FR-018 — everyone who consented, across every programme this
    company has run. The retention mechanism, and the strongest renewal argument.
    """
    from projet.models import Programme

    return (
        select(Person)
        .join(Application, Application.person_id == Person.id)
        .join(Programme, Application.programme_id == Programme.id)
        .where(Programme.company_id == company_id)
        .where(Application.consent_share_company.is_(True))
        .distinct()
    )


def company_visible_submissions(programme_id: uuid.UUID) -> Select:
    """FR-1051 — the submissions dashboard, consent-filtered like everything else."""
    return (
        select(Submission)
        .join(Team, Submission.team_id == Team.id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .join(Participant, TeamMember.participant_id == Participant.id)
        .join(Application, Participant.application_id == Application.id)
        .where(Team.programme_id == programme_id)
        .where(Application.consent_share_company.is_(True))
        .distinct()
    )


def recording_consented_participants(programme_id: uuid.UUID) -> Select:
    """Separate consent, separate query. Declining recording does not remove
    someone from the programme (FR-202)."""
    return (
        select(Participant)
        .join(Application, Participant.application_id == Application.id)
        .where(Participant.programme_id == programme_id)
        .where(Application.consent_recording.is_(True))
    )
