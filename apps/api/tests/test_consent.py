"""Section 8: consent is enforced at the query layer, not the UI.

The risk table says to write a test for this. These are those tests: a person
who declined sharing must not appear in any company-facing result, by
construction rather than by a hidden button.
"""

from __future__ import annotations

from projet.access import (
    company_candidate_pool,
    company_visible_applications,
    company_visible_participants,
    company_visible_submissions,
    recording_consented_participants,
)
from projet.services.teams import ensure_submission, ensure_team_for_participant


def test_non_consenting_applicant_is_invisible_to_the_company(
    session, programme, participant_factory
):
    consenting = participant_factory(name="Yes Person", consent_share=True)
    declining = participant_factory(name="No Person", consent_share=False)

    visible = list(session.scalars(company_visible_applications(programme.id)))
    person_ids = {a.person_id for a in visible}

    assert consenting.person_id in person_ids
    assert declining.person_id not in person_ids


def test_non_consenting_participant_is_invisible_to_the_company(
    session, programme, participant_factory
):
    consenting = participant_factory(consent_share=True)
    declining = participant_factory(consent_share=False)

    visible = {p.id for p in session.scalars(company_visible_participants(programme.id))}

    assert consenting.id in visible
    assert declining.id not in visible


def test_candidate_pool_excludes_non_consenting_people(
    session, company, programme, participant_factory
):
    consenting = participant_factory(consent_share=True)
    declining = participant_factory(consent_share=False)

    pool = {p.id for p in session.scalars(company_candidate_pool(company.id))}

    assert consenting.person_id in pool
    assert declining.person_id not in pool


def test_submissions_dashboard_excludes_non_consenting_people(
    session, programme, participant_factory
):
    consenting = participant_factory(consent_share=True)
    declining = participant_factory(consent_share=False)
    for participant in (consenting, declining):
        team = ensure_team_for_participant(session, participant)
        ensure_submission(session, team)

    visible = list(session.scalars(company_visible_submissions(programme.id)))
    teams = {s.team_id for s in visible}

    consenting_team = ensure_team_for_participant(session, consenting)
    declining_team = ensure_team_for_participant(session, declining)
    assert consenting_team.id in teams
    assert declining_team.id not in teams


def test_recording_consent_is_independent_of_sharing_consent(
    session, programme, participant_factory
):
    """FR-202 — the two consents are separate, and declining one does not
    imply the other."""
    shares_only = participant_factory(consent_share=True, consent_recording=False)
    records_only = participant_factory(consent_share=False, consent_recording=True)

    recordable = {p.id for p in session.scalars(recording_consented_participants(programme.id))}
    shareable = {p.id for p in session.scalars(company_visible_participants(programme.id))}

    assert shares_only.id in shareable and shares_only.id not in recordable
    assert records_only.id in recordable and records_only.id not in shareable
