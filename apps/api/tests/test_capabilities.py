"""The universal capability rollup (FR-903).

Skills are deliberately specific, which is what stops them compounding: three
programmes in three roles otherwise produce three unrelated lists. Capabilities
are the shared axis they roll up onto. Two things have to hold for that to be
worth anything — the map must stay joined to the skills taxonomy, and the
counting must never inflate a single attestation into two.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from projet.models import (
    Application,
    Capability,
    Company,
    CompanyUser,
    Participant,
    ProfileSkill,
    Programme,
    Score,
    ScoreSkillTag,
    Skill,
    SkillCapability,
)
from projet.models.enums import (
    ApplicationStatus,
    CompanyUserRole,
    ProgrammeStatus,
    SkillType,
)
from projet.seeds.loader import SeedError, _assert_capabilities_cover, load_content, seed_all
from projet.seeds.parsers import ContentError, parse_capabilities
from projet.seeds.parsers.capabilities import SkillCapabilities
from projet.services.profile import capability_rollup, promote_score_skill_tags
from projet.services.teams import ensure_team_for_participant

EXPECTED_CAPABILITIES = 7


# -- the content document ----------------------------------------------------


def test_the_vocabulary_stays_small_enough_to_read(content_dir):
    """A profile axis a reader cannot hold in their head is not an axis. Seven is
    already at the edge; a list that grows to twenty is just the skills taxonomy
    again, and compounds no better."""
    content = parse_capabilities(content_dir / "capabilities.md")
    assert len(content.capabilities) == EXPECTED_CAPABILITIES
    assert [c.sort_order for c in content.capabilities] == list(range(1, EXPECTED_CAPABILITIES + 1))
    assert all(c.summary for c in content.capabilities)


def test_every_skill_maps_onto_at_least_one_capability(content_dir):
    bundle = load_content(content_dir)
    ranked = {name for seed in bundle.roles for name in seed.hard_skills + seed.soft_skills}
    mapped = {entry.skill for entry in bundle.skill_capabilities}
    assert ranked == mapped


def test_no_capability_is_left_with_nothing_mapped_to_it(content_dir):
    """A capability nothing maps onto can never appear on a profile, so it is a
    word in a table rather than an axis."""
    content = parse_capabilities(content_dir / "capabilities.md")
    used = {name for entry in content.skill_map for name in entry.capabilities}
    assert {c.name for c in content.capabilities} == used


def test_capability_names_do_not_collide_with_skill_names(content_dir):
    """A profile showing a capability and a skill under the same word reads as a
    bug. This is why the third axis is 'Structuring' and not 'Synthesis'."""
    bundle = load_content(content_dir)
    skills = {name for (name, _kind) in bundle.skills}
    assert not {c.name for c in bundle.capabilities} & skills


def test_a_skill_naming_an_undefined_capability_is_rejected(tmp_path, content_dir):
    """The failure this prevents: a typo seeds nothing, and quietly splits one
    profile axis into two — half the evidence on each."""
    source = (content_dir / "capabilities.md").read_text(encoding="utf-8")
    broken = source.replace("| SQL | ", "| SQL | Quantitive analysis · ", 1)
    path = tmp_path / "capabilities.md"
    path.write_text(broken, encoding="utf-8")

    with pytest.raises(ContentError, match="undefined capabilities"):
        parse_capabilities(path)


def test_a_skill_with_no_capability_is_rejected(tmp_path, content_dir):
    source = (content_dir / "capabilities.md").read_text(encoding="utf-8")
    row = next(line for line in source.splitlines() if line.startswith("| SQL |"))
    path = tmp_path / "capabilities.md"
    path.write_text(source.replace(row, "| SQL |  |", 1), encoding="utf-8")

    with pytest.raises(ContentError, match="maps to no capability"):
        parse_capabilities(path)


def test_a_duplicate_skill_row_is_rejected(tmp_path, content_dir):
    """Two rows for one skill is an edit that half-landed, and whichever the
    parser took last would silently win."""
    source = (content_dir / "capabilities.md").read_text(encoding="utf-8")
    row = next(line for line in source.splitlines() if line.startswith("| SQL |"))
    path = tmp_path / "capabilities.md"
    path.write_text(source.replace(row, f"{row}\n{row}", 1), encoding="utf-8")

    with pytest.raises(ContentError, match="duplicate skill row"):
        parse_capabilities(path)


def test_the_map_and_the_taxonomy_must_agree_in_both_directions():
    """Both failures are silent in production: an unmapped skill never reaches a
    profile, and a stale row is how the two documents drift apart."""
    mapped = [SkillCapabilities(skill="SQL", capabilities=["Quantitative analysis"])]

    with pytest.raises(SeedError, match="no capability in capabilities.md"):
        _assert_capabilities_cover({"SQL", "Solidity"}, mapped)

    with pytest.raises(SeedError, match="not in skills.md"):
        _assert_capabilities_cover(set(), mapped)

    _assert_capabilities_cover({"SQL"}, mapped)


def test_a_skill_renamed_in_skills_md_alone_fails_the_seed(tmp_path, content_dir):
    """skills.md and capabilities.md join on skill name, exactly as the four role
    documents join on role name, and are held to the same standard."""
    for name in (
        "rubrics.md",
        "resources.md",
        "deliverables.md",
        "skills.md",
        "capabilities.md",
    ):
        (tmp_path / name).write_text(
            (content_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    skills = (tmp_path / "skills.md").read_text(encoding="utf-8")
    (tmp_path / "skills.md").write_text(skills.replace("SQL", "Structured Query Language"))

    with pytest.raises(SeedError, match="capability map and the skills taxonomy disagree"):
        load_content(tmp_path)


# -- seeding -----------------------------------------------------------------


def test_seeding_creates_the_vocabulary_and_the_links(session, content_dir):
    bundle = load_content(content_dir)
    report = seed_all(session, content_dir)

    assert report.capabilities_created == EXPECTED_CAPABILITIES
    assert report.capability_links_created == sum(
        len(entry.capabilities) for entry in bundle.skill_capabilities
    )
    assert session.query(Capability).count() == EXPECTED_CAPABILITIES

    # Every seeded skill can be reached from a capability, which is the join the
    # profile rollup depends on.
    linked = {row for row in session.scalars(select(SkillCapability.skill_id).distinct())}
    assert linked == {s.id for s in session.scalars(select(Skill))}


def test_re_seeding_changes_nothing(session, content_dir):
    seed_all(session, content_dir)
    before = session.query(SkillCapability).count()

    second = seed_all(session, content_dir)
    assert second.capabilities_created == 0
    assert second.capability_links_created == 0
    assert session.query(SkillCapability).count() == before


def test_re_mapping_a_skill_prunes_the_stale_link(session, tmp_path, content_dir):
    """A skill moved from one axis to another must actually leave the old one.
    Additive-only links would keep crediting an axis the content no longer
    claims, and nothing about the profile would look wrong."""
    for name in (
        "rubrics.md",
        "resources.md",
        "deliverables.md",
        "skills.md",
        "capabilities.md",
    ):
        (tmp_path / name).write_text(
            (content_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    seed_all(session, tmp_path)

    skill = session.scalar(select(Skill).where(Skill.name == "Financial modelling"))
    before = {
        session.get(Capability, link.capability_id).name
        for link in session.scalars(
            select(SkillCapability).where(SkillCapability.skill_id == skill.id)
        )
    }
    assert before == {"Quantitative analysis", "Technical craft"}

    source = (tmp_path / "capabilities.md").read_text(encoding="utf-8")
    row = next(line for line in source.splitlines() if line.startswith("| Financial modelling |"))
    (tmp_path / "capabilities.md").write_text(
        source.replace(row, "| Financial modelling | Quantitative analysis |", 1),
        encoding="utf-8",
    )
    seed_all(session, tmp_path)

    after = {
        session.get(Capability, link.capability_id).name
        for link in session.scalars(
            select(SkillCapability).where(SkillCapability.skill_id == skill.id)
        )
    }
    assert after == {"Quantitative analysis"}


# -- promotion and rollup ----------------------------------------------------


def _skill(session, name: str, kind: SkillType = SkillType.HARD) -> Skill:
    suffix = uuid.uuid4().hex[:6]
    skill = Skill(name=f"{name} {suffix}", slug=f"{name.lower()}-{suffix}", type=kind)
    session.add(skill)
    session.flush()
    return skill


def _capability(session, name: str, order: int = 1) -> Capability:
    suffix = uuid.uuid4().hex[:6]
    capability = Capability(
        name=f"{name} {suffix}",
        slug=f"{name.lower()}-{suffix}",
        summary=f"{name}, for the test.",
        sort_order=order,
    )
    session.add(capability)
    session.flush()
    return capability


def _judge(session, company_name: str, judge_name: str) -> CompanyUser:
    suffix = uuid.uuid4().hex[:6]
    company = Company(name=company_name, slug=f"{company_name.lower()}-{suffix}")
    session.add(company)
    session.flush()
    user = CompanyUser(
        company_id=company.id,
        name=judge_name,
        title="Principal Engineer",
        email=f"{suffix}@{company_name.lower()}.test",
        role=CompanyUserRole.REP,
    )
    session.add(user)
    session.flush()
    return user


def _score(session, participant, judge: CompanyUser, skills: list[Skill], *, minute: int = 0):
    team = ensure_team_for_participant(session, participant)
    score = Score(
        team_id=team.id,
        scorer_id=judge.id,
        created_at=datetime.now(UTC) + timedelta(minutes=minute),
    )
    session.add(score)
    session.flush()
    for skill in skills:
        session.add(
            ScoreSkillTag(score_id=score.id, participant_id=participant.id, skill_id=skill.id)
        )
    session.flush()
    return score


def test_promotion_carries_the_attester(session, participant_factory):
    participant = participant_factory()
    judge = _judge(session, "Acme", "Priya Judge")
    skill = _skill(session, "SQL")
    _score(session, participant, judge, [skill])

    assert promote_score_skill_tags(session, participant.id) == 1

    row = session.scalar(select(ProfileSkill).where(ProfileSkill.skill_id == skill.id))
    assert row.attested_by_name == "Priya Judge"
    assert row.attested_by_title == "Principal Engineer"
    assert row.attested_by_company == "Acme"


def test_promotion_is_idempotent_and_two_judges_make_one_line(session, participant_factory):
    """Re-running after a third judge scores must not rewrite who the profile
    credits, and a skill two judges both tagged is one attested skill, not two."""
    participant = participant_factory()
    skill = _skill(session, "SQL")
    first_judge = _judge(session, "Acme", "Priya Judge")
    _score(session, participant, first_judge, [skill], minute=0)

    assert promote_score_skill_tags(session, participant.id) == 1
    assert promote_score_skill_tags(session, participant.id) == 0

    second_judge = _judge(session, "Beta", "Wei Judge")
    _score(session, participant, second_judge, [skill], minute=5)
    assert promote_score_skill_tags(session, participant.id) == 0

    rows = list(session.scalars(select(ProfileSkill).where(ProfileSkill.skill_id == skill.id)))
    assert len(rows) == 1
    assert rows[0].attested_by_name == "Priya Judge"


def test_the_rollup_groups_skills_onto_their_axes(session, participant_factory):
    participant = participant_factory()
    judge = _judge(session, "Acme", "Priya Judge")
    craft = _capability(session, "Technical craft", order=1)
    communication = _capability(session, "Communication", order=2)

    sql = _skill(session, "SQL")
    writing = _skill(session, "Writing", SkillType.SOFT)
    session.add_all(
        [
            SkillCapability(skill_id=sql.id, capability_id=craft.id),
            SkillCapability(skill_id=writing.id, capability_id=communication.id),
        ]
    )
    _score(session, participant, judge, [sql, writing])
    promote_score_skill_tags(session, participant.id)

    rollup = capability_rollup(session, participant.person_id)
    assert [c.name for c in rollup] == [craft.name, communication.name]
    assert [s.name for s in rollup[0].skills] == [sql.name]
    assert rollup[0].skills[0].attesters == ["Priya Judge"]


def test_a_skill_on_two_axes_is_not_counted_twice(session, participant_factory):
    """One attestation must not look like two. A profile that inflates is worse
    than no profile — it is the one claim a hiring signal cannot afford."""
    participant = participant_factory()
    judge = _judge(session, "Acme", "Priya Judge")
    craft = _capability(session, "Technical craft", order=1)
    quant = _capability(session, "Quantitative analysis", order=2)

    sql = _skill(session, "SQL")
    session.add_all(
        [
            SkillCapability(skill_id=sql.id, capability_id=craft.id),
            SkillCapability(skill_id=sql.id, capability_id=quant.id),
        ]
    )
    _score(session, participant, judge, [sql])
    promote_score_skill_tags(session, participant.id)

    rollup = capability_rollup(session, participant.person_id)
    assert len(rollup) == 2
    for entry in rollup:
        assert entry.programme_count == 1
        assert entry.attester_count == 1


def test_capabilities_with_no_evidence_are_omitted(session, participant_factory):
    """An empty axis on a profile reads as a weakness the platform never
    measured."""
    participant = participant_factory()
    judge = _judge(session, "Acme", "Priya Judge")
    craft = _capability(session, "Technical craft", order=1)
    _capability(session, "Judgement", order=2)

    sql = _skill(session, "SQL")
    session.add(SkillCapability(skill_id=sql.id, capability_id=craft.id))
    _score(session, participant, judge, [sql])
    promote_score_skill_tags(session, participant.id)

    assert [c.name for c in capability_rollup(session, participant.person_id)] == [craft.name]


def test_a_hidden_profile_skill_leaves_the_rollup(session, participant_factory):
    """FR-903d lets a participant hide an attested skill. Hiding it on the
    profile but leaving it counted on the axis above would defeat the control."""
    participant = participant_factory()
    judge = _judge(session, "Acme", "Priya Judge")
    craft = _capability(session, "Technical craft")
    sql = _skill(session, "SQL")
    session.add(SkillCapability(skill_id=sql.id, capability_id=craft.id))
    _score(session, participant, judge, [sql])
    promote_score_skill_tags(session, participant.id)

    row = session.scalar(select(ProfileSkill).where(ProfileSkill.skill_id == sql.id))
    row.visible = False
    session.flush()

    assert capability_rollup(session, participant.person_id) == []
    assert len(capability_rollup(session, participant.person_id, include_hidden=True)) == 1


def test_a_second_programme_compounds_onto_the_same_axis(
    session, company, role, participant_factory
):
    """The whole point of the rollup. Two programmes in different roles tag
    different specific skills; the profile has to show one axis with two
    programmes behind it, not two unrelated lists."""
    craft = _capability(session, "Technical craft")
    first_participant = participant_factory()
    sql = _skill(session, "SQL")
    solidity = _skill(session, "Solidity")
    session.add_all(
        [
            SkillCapability(skill_id=sql.id, capability_id=craft.id),
            SkillCapability(skill_id=solidity.id, capability_id=craft.id),
        ]
    )
    _score(session, first_participant, _judge(session, "Acme", "Priya Judge"), [sql])
    promote_score_skill_tags(session, first_participant.id)

    now = datetime.now(UTC)
    second_programme = Programme(
        company_id=company.id,
        role_id=role.id,
        title="Settlement contract audit",
        slug=f"audit-{uuid.uuid4().hex[:6]}",
        start_at=now,
        submit_deadline_at=now + timedelta(days=6),
        status=ProgrammeStatus.RUNNING,
    )
    session.add(second_programme)
    session.flush()
    application = Application(
        programme_id=second_programme.id,
        person_id=first_participant.person_id,
        consent_share_company=True,
        consent_captured_at=now,
        status=ApplicationStatus.ACCEPTED,
    )
    session.add(application)
    session.flush()
    second_participant = Participant(
        application_id=application.id,
        programme_id=second_programme.id,
        person_id=first_participant.person_id,
    )
    session.add(second_participant)
    session.flush()
    _score(session, second_participant, _judge(session, "Beta", "Wei Judge"), [solidity])
    promote_score_skill_tags(session, second_participant.id)

    rollup = capability_rollup(session, first_participant.person_id)
    assert len(rollup) == 1
    assert {s.name for s in rollup[0].skills} == {sql.name, solidity.name}
    assert rollup[0].programme_count == 2
    assert rollup[0].attester_count == 2
