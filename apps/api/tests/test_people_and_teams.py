"""Person reuse and team-always.

Section 4 calls Person-separate-from-Application the single most important
modelling decision in the document: get it wrong and the profile never
compounds. These tests are what hold it.
"""

from __future__ import annotations

import pytest

from projet.models import Person, Submission, TeamMember
from projet.services.people import google_email_warning, resolve_person
from projet.services.teams import (
    add_team_member,
    ensure_submission,
    ensure_team_for_participant,
)


def test_a_returning_person_resolves_to_the_same_record(session):
    first, created_first = resolve_person(
        session, name="Sam Student", contact_email="sam@school.edu"
    )
    second, created_second = resolve_person(
        session, name="Sam Student", contact_email="sam@school.edu", job_title="Analyst"
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert session.query(Person).count() == 1


def test_person_matching_is_case_and_whitespace_insensitive(session):
    first, _ = resolve_person(session, name="Sam", contact_email="Sam@School.edu")
    second, created = resolve_person(session, name="Sam", contact_email="  sam@school.edu ")

    assert created is False
    assert first.id == second.id


def test_a_person_is_matched_on_their_google_address_too(session):
    first, _ = resolve_person(
        session, name="Sam", contact_email="sam@school.edu", google_email="sam@gmail.com"
    )
    # Applies next cohort using the Google address as their contact address.
    second, created = resolve_person(session, name="Sam", contact_email="sam@gmail.com")

    assert created is False
    assert first.id == second.id


def test_returning_details_are_refreshed_not_duplicated(session):
    resolve_person(
        session, name="Sam", contact_email="sam@school.edu", organisation="NUS", year_course="Y2"
    )
    person, _ = resolve_person(
        session, name="Sam", contact_email="sam@school.edu", organisation="NUS", year_course="Y3"
    )

    assert person.year_course == "Y3"
    assert session.query(Person).count() == 1


def test_every_participant_gets_a_team_even_solo(session, participant_factory):
    """Submissions always resolve through a team, so hackathon pairs need no
    retrofit once live data exists."""
    participant = participant_factory()
    team = ensure_team_for_participant(session, participant)

    members = session.query(TeamMember).filter(TeamMember.team_id == team.id).all()
    assert len(members) == 1
    assert members[0].participant_id == participant.id


def test_ensure_team_is_idempotent(session, participant_factory):
    participant = participant_factory()
    first = ensure_team_for_participant(session, participant)
    second = ensure_team_for_participant(session, participant)
    assert first.id == second.id


def test_a_solo_programme_refuses_a_second_team_member(session, programme, participant_factory):
    one = participant_factory()
    two = participant_factory()
    team = ensure_team_for_participant(session, one)

    assert programme.team_size_max == 1
    with pytest.raises(ValueError, match="team is full"):
        add_team_member(session, team, two)


def test_a_paired_programme_accepts_two(session, programme, participant_factory):
    programme.team_size_max = 2
    session.flush()
    one = participant_factory()
    two = participant_factory()
    team = ensure_team_for_participant(session, one)
    add_team_member(session, team, two)

    members = session.query(TeamMember).filter(TeamMember.team_id == team.id).all()
    assert len(members) == 2


def test_submission_slots_are_seeded_once(session, participant_factory):
    participant = participant_factory()
    team = ensure_team_for_participant(session, participant)
    first = ensure_submission(session, team)
    second = ensure_submission(session, team)

    assert first.id == second.id
    assert session.query(Submission).count() == 1
    assert {link.slot.value for link in first.links} == {"artifact", "memo"}


@pytest.mark.parametrize(
    "email,warns",
    [
        ("sam@gmail.com", False),
        ("sam@nus.edu.sg", False),
        ("sam@outlook.com", True),
        ("sam@yahoo.com", True),
        ("sam@proton.me", True),
        ("not-an-email", True),
    ],
)
def test_google_email_warning_warns_without_blocking(email, warns):
    """FR-204 — a warning, never a hard block: some organisations run Google on
    a custom domain."""
    assert (google_email_warning(email) is not None) is warns
