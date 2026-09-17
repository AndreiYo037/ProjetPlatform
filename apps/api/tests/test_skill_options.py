"""Ordering the skill taxonomy for the judge who has to pick from it.

FR-903b — the failure mode this exists to prevent is a judge with ninety
seconds scrolling an alphabetical list of hundreds and tagging whatever
starts with "A".
"""

from __future__ import annotations

from projet.models import Skill
from projet.models.enums import SkillType
from projet.services.skills import options_for_role


def _skill(session, name: str, kind: SkillType = SkillType.HARD) -> Skill:
    skill = Skill(name=name, slug=name.lower().replace(" ", "-"), type=kind)
    session.add(skill)
    session.flush()
    return skill


def test_the_roles_ranked_skills_come_first_in_their_ranked_order(session, role):
    """The template ranks SQL then Data cleaning; that is the order, not
    alphabetical — which would put Data cleaning first."""
    for name in ("Zebra husbandry", "Data cleaning", "SQL", "Apple grading"):
        _skill(session, name)
    _skill(session, "Attention to detail", SkillType.SOFT)

    options = options_for_role(session, role.id)

    assert [o.skill.name for o in options[:3]] == ["SQL", "Data cleaning", "Attention to detail"]
    assert [o.suggested for o in options[:3]] == [True, True, True]


def test_everything_else_follows_alphabetically_and_unsuggested(session, role):
    for name in ("Zebra husbandry", "Apple grading", "SQL"):
        _skill(session, name)

    options = options_for_role(session, role.id)
    rest = [o for o in options if not o.suggested]

    assert [o.skill.name for o in rest] == ["Apple grading", "Zebra husbandry"]


def test_the_whole_taxonomy_is_still_reachable(session, role):
    """Ranking reorders; it never hides. Typing has to reach everything."""
    for name in ("SQL", "Apple grading", "Zebra husbandry"):
        _skill(session, name)

    options = options_for_role(session, role.id)
    assert len(options) == 3


def test_a_skill_is_never_offered_twice(session, role):
    """A name in both ranked lists, or ranked and then swept up by the
    alphabetical remainder, would otherwise appear twice."""
    _skill(session, "SQL")
    _skill(session, "Data cleaning")

    options = options_for_role(session, role.id)
    names = [o.skill.name for o in options]
    assert len(names) == len(set(names))


def test_a_template_naming_a_skill_the_taxonomy_lacks_is_skipped(session, role):
    """A seed gap should not blow up a scoring card mid-pitch."""
    _skill(session, "SQL")  # "Data cleaning" and "Attention to detail" absent

    options = options_for_role(session, role.id)
    assert [o.skill.name for o in options] == ["SQL"]


def test_no_role_still_returns_the_taxonomy_alphabetically(session):
    for name in ("Zebra husbandry", "Apple grading"):
        _skill(session, name)

    options = options_for_role(session, None)
    assert [o.skill.name for o in options] == ["Apple grading", "Zebra husbandry"]
    assert all(not o.suggested for o in options)
