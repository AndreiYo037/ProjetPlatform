"""Editing a project — what each kind of entry will and will not accept.

The boundary this file defends: on a verified entry the description is theirs
and the facts are the platform's, and a skill on a verified entry is a judge's
attestation rather than anything the participant can type.
"""

from __future__ import annotations

import uuid

import pytest

from projet.models import ProjectEntry, Skill
from projet.models.enums import ArtifactVisibility, ProgrammeStatus, SkillType
from projet.models.portfolio import ProjectSkill
from projet.services.projects import (
    ProjectError,
    add_link,
    attach_file,
    create_entry,
    delete_entry,
    remove_link,
    seed_from_participant,
    set_skills,
    update_entry,
)
from projet.storage import get_storage

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def verified(session, programme, participant_factory):
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()
    participant = participant_factory()
    return seed_from_participant(session, participant.person_id, participant.id)


@pytest.fixture
def mine(session, participant_factory):
    participant = participant_factory()
    return create_entry(session, participant.person_id, title="Weekend build")


def _skill(session, name="Rust"):
    skill = Skill(name=name, slug=name.lower(), type=SkillType.HARD)
    session.add(skill)
    session.flush()
    return skill


def test_the_description_on_a_verified_entry_is_theirs_to_write(session, verified):
    updated = update_entry(
        session, verified.person_id, verified.id, {"description": "Churn was measured monthly."}
    )
    assert updated.description == "Churn was measured monthly."


def test_the_facts_on_a_verified_entry_are_not(session, verified):
    """Rewriting who they worked for is refused with a named error, not
    silently dropped — an edit that vanishes is worse than one that fails."""
    for field, value in (
        ("title", "Something else"),
        ("associated_experience", "A more impressive company"),
        ("ongoing", True),
    ):
        with pytest.raises(ProjectError, match="Cannot change"):
            update_entry(session, verified.person_id, verified.id, {field: value})


def test_a_self_declared_entry_accepts_every_field(session, mine):
    updated = update_entry(
        session,
        mine.person_id,
        mine.id,
        {"title": "Renamed", "associated_experience": "Self", "description": "A story."},
    )

    assert updated.title == "Renamed"
    assert updated.associated_experience == "Self"
    assert updated.description == "A story."


def test_marking_it_ongoing_clears_the_end_date(session, mine):
    """The two contradict each other, and the flag is what they ticked last."""
    from datetime import date

    update_entry(session, mine.person_id, mine.id, {"ended_at": date(2026, 1, 1)})
    updated = update_entry(session, mine.person_id, mine.id, {"ongoing": True})

    assert updated.ongoing is True
    assert updated.ended_at is None


def test_consent_to_show_the_work_is_editable_on_both(session, verified, mine):
    for entry in (verified, mine):
        updated = update_entry(
            session, entry.person_id, entry.id, {"artifact_visibility": ArtifactVisibility.PUBLIC}
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


def test_deleting_an_entry_takes_its_uploaded_files_with_it(session, mine):
    """An orphaned object nobody can reach is still the work sitting on disk."""
    link = attach_file(
        session, mine.person_id, mine.id, filename="shot.png", content_type="image/png", data=PNG
    )
    key = link.storage_key
    assert get_storage().exists(key)

    delete_entry(session, mine.person_id, mine.id)
    assert not get_storage().exists(key)


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
        session, mine.person_id, mine.id, url="https://github.test/repo", label="The code"
    )
    assert [link_.url for link_ in mine.links] == ["https://github.test/repo"]

    remove_link(session, mine.person_id, mine.id, link.id)
    session.refresh(mine)
    assert mine.links == []


def test_a_file_can_be_attached_and_is_stored_privately(session, mine):
    link = attach_file(
        session, mine.person_id, mine.id, filename="shot.png", content_type="image/png", data=PNG
    )

    assert link.is_file is True
    assert link.url is None
    assert link.filename == "shot.png"
    # Never guessable from the entry alone: the key carries a random segment.
    assert link.storage_key.startswith(f"projects/{mine.id}/")
    assert get_storage().get(link.storage_key) == PNG


def test_removing_a_file_deletes_the_object(session, mine):
    link = attach_file(
        session, mine.person_id, mine.id, filename="shot.png", content_type="image/png", data=PNG
    )
    key = link.storage_key

    remove_link(session, mine.person_id, mine.id, link.id)
    assert not get_storage().exists(key)


def test_an_oversized_file_is_refused(session, mine):
    with pytest.raises(ProjectError, match="larger than"):
        attach_file(
            session,
            mine.person_id,
            mine.id,
            filename="big.png",
            content_type="image/png",
            data=b"0" * (20 * 1024 * 1024 + 1),
        )


def test_an_unaccepted_file_type_is_refused(session, mine):
    with pytest.raises(ProjectError, match="not accepted"):
        attach_file(
            session,
            mine.person_id,
            mine.id,
            filename="run.exe",
            content_type="application/x-msdownload",
            data=b"MZ",
        )


def test_you_cannot_attach_a_file_to_someone_elses_project(session, mine, participant_factory):
    stranger = participant_factory(name="Someone Else")

    with pytest.raises(ProjectError, match="No project"):
        attach_file(
            session,
            stranger.person_id,
            mine.id,
            filename="shot.png",
            content_type="image/png",
            data=PNG,
        )


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
