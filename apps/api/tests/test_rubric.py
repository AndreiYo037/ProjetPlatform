"""Criteria-as-data (FR-070).

The PRD says this lands in Milestone 1 and not later, because retrofitting it
after live score data exists means migrating every scored pitch. These tests
hold the rules that make a score comparable across cohorts.
"""

from __future__ import annotations

import pytest

from projet.models import RubricCriterion
from projet.models.enums import ProgrammeStatus
from projet.services.rubric import (
    RubricError,
    compose_rubric,
    edit_criterion,
    publish,
    universal_criteria,
    validate_for_publication,
)


def test_universal_criteria_are_slots_one_and_four(content_dir):
    criteria = universal_criteria(content_dir)
    assert [c.slot for c in criteria] == [1, 4]
    assert criteria[0].name == "Problem understanding"
    assert criteria[1].name == "Defence under questioning"
    assert all(c.anchor_5 and c.anchor_3 and c.anchor_1 for c in criteria)


def test_compose_seeds_four_criteria_from_universal_pair_and_role_template(
    session, programme, content_dir
):
    criteria = compose_rubric(session, programme, content_dir)

    assert [c.slot for c in criteria] == [1, 2, 3, 4]
    assert criteria[0].name == "Problem understanding"
    assert criteria[3].name == "Defence under questioning"
    # Slots 2 and 3 come from the role template (FR-055, FR-073).
    assert criteria[1].name == "Data handling"
    assert criteria[2].name == "Insight to decision"
    assert all(c.is_complete for c in criteria)


def test_compose_is_idempotent(session, programme, content_dir):
    compose_rubric(session, programme, content_dir)
    session.flush()
    compose_rubric(session, programme, content_dir)
    session.flush()

    count = (
        session.query(RubricCriterion).filter(RubricCriterion.programme_id == programme.id).count()
    )
    assert count == 4


def test_universal_slots_cannot_be_renamed(session, programme, content_dir):
    criteria = compose_rubric(session, programme, content_dir)
    slot_one = criteria[0]

    with pytest.raises(RubricError, match="cannot be renamed"):
        edit_criterion(session, slot_one, name="Something bespoke")


def test_universal_anchors_can_still_be_edited(session, programme, content_dir):
    """FR-072 — admin may edit the anchors, just not the names."""
    criteria = compose_rubric(session, programme, content_dir)
    edit_criterion(session, criteria[0], anchor_5="Host's own phrasing here")
    assert criteria[0].anchor_5 == "Host's own phrasing here"


def test_role_slots_can_be_renamed_and_rewritten(session, programme, content_dir):
    """FR-074 — 'use host's phrasing' on the 5 anchor."""
    criteria = compose_rubric(session, programme, content_dir)
    edit_criterion(
        session,
        criteria[1],
        name="Data craft",
        anchor_5="Caught the thing our own analyst missed",
    )
    assert criteria[1].name == "Data craft"


def test_criteria_are_immutable_once_judging(session, programme, content_dir):
    """FR-076 — editing now would invalidate scores already entered."""
    criteria = compose_rubric(session, programme, content_dir)
    programme.status = ProgrammeStatus.JUDGING
    session.flush()

    with pytest.raises(RubricError, match="immutable"):
        edit_criterion(session, criteria[1], anchor_5="too late")


def test_publication_is_blocked_by_an_incomplete_rubric(session, programme, content_dir):
    """FR-075 — validation blocks draft -> open."""
    criteria = compose_rubric(session, programme, content_dir)
    criteria[2].anchor_1 = None
    session.flush()

    problems = validate_for_publication(session, programme)
    assert problems and "slot 3" in problems[0]

    with pytest.raises(RubricError, match="incomplete rubric"):
        publish(session, programme)


def test_publication_succeeds_with_a_complete_rubric(session, programme, content_dir):
    compose_rubric(session, programme, content_dir)
    programme.status = ProgrammeStatus.DRAFT
    publish(session, programme)
    assert programme.status == ProgrammeStatus.OPEN


def test_criteria_are_per_programme_so_improving_one_never_rewrites_history(
    session, company, role, programme, content_dir
):
    """FR-077 — a better rubric next cohort must not rewrite the last one."""
    from projet.models import Programme

    first = compose_rubric(session, programme, content_dir)
    edit_criterion(session, first[1], name="Season one wording")

    second_programme = Programme(
        company_id=company.id, role_id=role.id, title="Cohort 2", slug="cohort-2"
    )
    session.add(second_programme)
    session.flush()
    second = compose_rubric(session, second_programme, content_dir)

    assert first[1].name == "Season one wording"
    assert second[1].name == "Data handling"
    assert first[1].id != second[1].id
