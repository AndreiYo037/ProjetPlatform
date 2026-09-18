"""Editing a case study — what each kind of entry will and will not accept.

The boundary this file defends: on a verified entry the narrative is theirs
and the facts are the platform's, and a skill on a verified entry is a judge's
attestation rather than anything the participant can type.
"""

from __future__ import annotations

import uuid

import pytest

from projet.models import ProjectEntry, Skill
from projet.models.enums import (
    ArtifactVisibility,
    ProgrammeStatus,
    ProjectKind,
    ProjectLinkKind,
    SkillType,
)
from projet.models.portfolio import ProjectSkill
from projet.services.projects import (
    ProjectError,
    add_link,
    create_entry,
    delete_entry,
    remove_link,
    seed_from_participant,
    set_skills,
    update_entry,
)


@pytest.fixture
def verified(session, programme, participant_factory):
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()
    participant = participant_factory()
    return seed_from_participant(session, participant.person_id, participant.id)


@pytest.fixture
def mine(session, participant_factory):
    participant = participant_factory()
    return create_entry(
        session,
        participant.person_id,
        kind=ProjectKind.HACKATHON,
        title="Weekend build",
    )


def _skill(session, name="Rust"):
    skill = Skill(name=name, slug=name.lower(), type=SkillType.HARD)
    session.add(skill)
    session.flush()
    return skill


def test_a_self_declared_entry_cannot_claim_to_be_a_programme(session, participant_factory):
    """PROGRAMME is what a seeded entry is. If anyone could type it, a claim
    and a week a company watched would look identical on the page."""
    participant = participant_factory()

    with pytest.raises(ProjectError, match="reserved"):
        create_entry(
            session, participant.person_id, kind=ProjectKind.PROGRAMME, title="Not really"
        )


def test_the_narrative_on_a_verified_entry_is_theirs_to_write(session, verified):
    updated = update_entry(
        session,
        verified.person_id,
        verified.id,
        {"problem": "Churn was measured monthly.", "outcome": "Flags a week earlier."},
    )

    assert updated.problem == "Churn was measured monthly."
    assert updated.outcome == "Flags a week earlier."


def test_the_facts_on_a_verified_entry_are_not(session, verified):
    """Rewriting who they worked for is refused with a named error, not
    silently dropped — an edit that vanishes is worse than one that fails."""
    for field, value in (
        ("title", "Something else"),
        ("organisation_name", "A more impressive company"),
        ("kind", ProjectKind.INTERNSHIP),
    ):
        with pytest.raises(ProjectError, match="Cannot change"):
            update_entry(session, verified.person_id, verified.id, {field: value})


def test_a_self_declared_entry_accepts_every_field(session, mine):
    updated = update_entry(
        session,
        mine.person_id,
        mine.id,
        {"title": "Renamed", "organisation_name": "Self", "kind": ProjectKind.COMPETITION},
    )

    assert updated.title == "Renamed"
    assert updated.kind is ProjectKind.COMPETITION


def test_consent_to_show_artifacts_is_editable_on_both(session, verified, mine):
    for entry in (verified, mine):
        updated = update_entry(
            session,
            entry.person_id,
            entry.id,
            {"artifact_visibility": ArtifactVisibility.PUBLIC},
        )
        assert updated.artifact_visibility is ArtifactVisibility.PUBLIC


def test_a_verified_entry_can_be_hidden_but_not_deleted(session, verified):
    """It is a record of a week this platform ran. Hiding is theirs; erasing
    the record is not."""
    hidden = update_entry(session, verified.person_id, verified.id, {"visible": False})
    assert hidden.visible is False

    with pytest.raises(ProjectError, match="hidden, not deleted"):
        delete_entry(session, verified.person_id, verified.id)


def test_a_self_declared_entry_can_be_deleted(session, mine):
    delete_entry(session, mine.person_id, mine.id)
    assert session.get(ProjectEntry, mine.id) is None


def test_you_cannot_edit_an_entry_that_is_not_yours(session, mine, participant_factory):
    stranger = participant_factory(name="Someone Else")

    with pytest.raises(ProjectError, match="No project"):
        update_entry(session, stranger.person_id, mine.id, {"title": "Mine now"})


def test_an_entry_that_does_not_exist_answers_the_same_way(session, mine):
    """Same error as someone else's entry, so the response cannot be used to
    learn that an entry exists."""
    with pytest.raises(ProjectError, match="No project"):
        update_entry(session, mine.person_id, uuid.uuid4(), {"title": "x"})


def test_links_can_be_added_and_removed(session, mine):
    link = add_link(
        session,
        mine.person_id,
        mine.id,
        kind=ProjectLinkKind.GITHUB,
        url="https://github.test/repo",
        label="The code",
    )
    assert [link_.url for link_ in mine.links] == ["https://github.test/repo"]

    remove_link(session, mine.person_id, mine.id, link.id)
    session.refresh(mine)
    assert mine.links == []


def test_skills_on_a_self_declared_entry_are_a_claim_they_can_set(session, mine):
    rust = _skill(session, "Rust")
    go = _skill(session, "Go")

    set_skills(session, mine.person_id, mine.id, [rust.id, go.id])
    assert {ps.skill_id for ps in mine.skills} == {rust.id, go.id}

    # Replacing, not appending: the list sent is the list kept.
    set_skills(session, mine.person_id, mine.id, [go.id])
    session.refresh(mine)
    assert {ps.skill_id for ps in mine.skills} == {go.id}


def test_skills_on_a_verified_entry_come_from_attestation_only(session, verified):
    """A participant typing a skill onto a week a judge watched would make a
    claim indistinguishable from that judge's attestation."""
    rust = _skill(session, "Rust")

    with pytest.raises(ProjectError, match="attestation"):
        set_skills(session, verified.person_id, verified.id, [rust.id])

    assert session.query(ProjectSkill).count() == 0


def test_an_unknown_skill_is_refused(session, mine):
    with pytest.raises(ProjectError, match="Unknown skill"):
        set_skills(session, mine.person_id, mine.id, [uuid.uuid4()])
