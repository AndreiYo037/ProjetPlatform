"""Case-study entries — verified and self-declared, never confused.

The load-bearing rule this file defends: a verified entry verifies the facts
(who, when, the brief) and never the narrative, and self-declared work is
counted and shown but can never outrank a week a company watched.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from projet.models import ProjectEntry, Skill
from projet.models.enums import (
    ArtifactVisibility,
    ProgrammeStatus,
    ProjectKind,
    ProjectLinkKind,
    SkillType,
)
from projet.models.portfolio import ProjectSkill
from projet.services.projects import ProjectError, entries_for, seed_from_participant


@pytest.fixture
def completed(session, programme, participant_factory):
    programme.brief_url = "https://example.test/brief"
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()
    return participant_factory()


def test_seeding_copies_the_facts_and_leaves_the_narrative_empty(session, completed, programme, company):
    """The participant writes the story. The platform vouches for the setting."""
    entry = seed_from_participant(session, completed.person_id, completed.id)

    assert entry.verified is True
    assert entry.kind is ProjectKind.PROGRAMME
    assert entry.title == programme.title
    assert entry.organisation_name == company.name
    assert entry.started_at == programme.start_at.date()
    assert entry.ended_at == programme.submit_deadline_at.date()

    assert entry.problem is None
    assert entry.approach is None
    assert entry.contribution == []
    assert entry.outcome is None


def test_the_brief_comes_across_but_nothing_else_does(session, completed):
    """The brief is the company's own published text. The submission is not:
    it can carry their data pack, which needs its own act of consent."""
    entry = seed_from_participant(session, completed.person_id, completed.id)

    assert [(link.kind, link.url) for link in entry.links] == [
        (ProjectLinkKind.BRIEF, "https://example.test/brief")
    ]


def test_artifacts_start_private(session, completed):
    """The consent given to one company for one week of judging is not consent
    to a public profile for ever."""
    entry = seed_from_participant(session, completed.person_id, completed.id)
    assert entry.artifact_visibility is ArtifactVisibility.PRIVATE


def test_seeding_twice_does_not_wipe_what_they_wrote(session, completed):
    """A second click must be harmless, not destructive."""
    first = seed_from_participant(session, completed.person_id, completed.id)
    first.problem = "Churn was measured monthly and acted on quarterly."
    session.flush()

    second = seed_from_participant(session, completed.person_id, completed.id)

    assert second.id == first.id
    assert second.problem == "Churn was measured monthly and acted on quarterly."
    assert session.query(ProjectEntry).count() == 1


def test_a_programme_still_running_has_nothing_to_show_yet(session, programme, participant_factory):
    programme.status = ProgrammeStatus.RUNNING
    session.flush()
    participant = participant_factory()

    with pytest.raises(ProjectError, match="not finished"):
        seed_from_participant(session, participant.person_id, participant.id)


def test_you_cannot_seed_someone_elses_programme(session, programme, participant_factory):
    programme.status = ProgrammeStatus.COMPLETE
    session.flush()
    mine = participant_factory()
    theirs = participant_factory(name="Other Person")

    with pytest.raises(ProjectError, match="not yours"):
        seed_from_participant(session, mine.person_id, theirs.id)


def test_verified_work_sorts_ahead_of_anything_self_declared(session, completed):
    """However recent or however well written the self-declared entry is."""
    verified = seed_from_participant(session, completed.person_id, completed.id)
    session.add(
        ProjectEntry(
            person_id=completed.person_id,
            kind=ProjectKind.HACKATHON,
            title="Weekend build",
            ended_at=date(2030, 1, 1),
        )
    )
    session.flush()

    ordered = entries_for(session, completed.person_id)

    assert [e.verified for e in ordered] == [True, False]
    assert ordered[0].id == verified.id


def test_a_hidden_entry_is_left_out(session, completed):
    entry = seed_from_participant(session, completed.person_id, completed.id)
    entry.visible = False
    session.flush()

    assert entries_for(session, completed.person_id) == []
    assert len(entries_for(session, completed.person_id, include_hidden=True)) == 1


def test_a_claimed_skill_never_lands_in_the_attested_table(session, completed):
    """ProjectSkill and ProfileSkill are separate tables so that a query for
    attested evidence cannot sweep up a claim by forgetting a WHERE clause."""
    skill = Skill(name="Rust", slug="rust", type=SkillType.HARD)
    session.add(skill)
    session.flush()

    entry = ProjectEntry(
        person_id=completed.person_id,
        kind=ProjectKind.INDEPENDENT,
        title="Compiler toy",
    )
    session.add(entry)
    session.flush()
    session.add(ProjectSkill(project_entry_id=entry.id, skill_id=skill.id))
    session.flush()

    from projet.models import ProfileSkill

    assert session.query(ProfileSkill).count() == 0
    assert session.query(ProjectSkill).count() == 1


def test_the_same_skill_cannot_be_claimed_twice_on_one_project(session, completed):
    skill = Skill(name="Go", slug="go", type=SkillType.HARD)
    session.add(skill)
    entry = ProjectEntry(
        person_id=completed.person_id, kind=ProjectKind.FREELANCE, title="A thing"
    )
    session.add(entry)
    session.flush()
    session.add(ProjectSkill(project_entry_id=entry.id, skill_id=skill.id))
    session.flush()
    session.add(ProjectSkill(project_entry_id=entry.id, skill_id=skill.id))

    with pytest.raises(IntegrityError):
        session.flush()


def test_a_profile_is_not_public_until_somebody_says_so(session, completed):
    """Off by default: a profile becomes public by an act, never by
    accumulating enough evidence."""
    from projet.models import Person

    person = session.get(Person, completed.person_id)
    assert person.public is False


def test_seeding_a_participant_that_does_not_exist_is_refused(session, completed):
    with pytest.raises(ProjectError, match="not yours"):
        seed_from_participant(session, completed.person_id, uuid.uuid4())
