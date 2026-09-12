"""Content parsing and seeding.

The three supplied documents are cross-cutting — each covers all 75 roles for
one aspect — so the join across them is where drift would appear. These tests
make drift a loud failure rather than a missing deliverable nobody notices.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from projet.models import DataPackResource, Role, RoleTemplate, Skill
from projet.models.enums import SkillType, VerificationStatus
from projet.seeds.loader import (
    SeedError,
    check_slug_lock,
    load_content,
    read_slug_lock,
    seed_all,
)
from projet.seeds.parsers import ContentError, parse_rubrics
from projet.seeds.parsers.common import slugify

EXPECTED_ROLES = 75
EXPECTED_CLUSTERS = 11


def test_all_four_documents_cover_the_same_roles(content_dir):
    bundle = load_content(content_dir)
    assert len(bundle.roles) == EXPECTED_ROLES
    assert len({r.cluster for r in bundle.roles}) == EXPECTED_CLUSTERS


def test_every_role_has_a_complete_template(content_dir):
    bundle = load_content(content_dir)
    for role in bundle.roles:
        assert role.deliverable, f"{role.name} has no deliverable"
        assert role.slot2.name and role.slot3.name, f"{role.name} has an unnamed criterion"
        for spec in (role.slot2, role.slot3):
            assert spec.anchor_5 and spec.anchor_3 and spec.anchor_1, (
                f"{role.name} slot {spec.slot} is missing an anchor"
            )
        assert role.hard_skills and role.soft_skills, f"{role.name} has no ranked skills"
        assert role.public_sources, f"{role.name} has no public sources"


def test_company_asks_are_split_by_friction_tier(content_dir):
    """FR-042 — the [E]/[M]/[H] tags are the whole point of that column, and the
    design rule depends on every challenge being completable from public plus [E]."""
    bundle = load_content(content_dir)
    by_name = {r.name: r for r in bundle.roles}

    healthcare = by_name["Healthcare Analytics"]
    assert healthcare.asks_hard == ["any patient-level data — never ask"]
    assert "pathway description" in healthcare.asks_easy

    assert all(r.asks_easy for r in bundle.roles), "every role needs at least one easy ask"


def test_at_risk_roles_carry_a_delivery_note(content_dir):
    """The deliverables doc flags four roles as tight inside six days."""
    bundle = load_content(content_dir)
    flagged = {r.name for r in bundle.roles if r.delivery_risk_note}
    assert flagged == {
        "Consumer Insights",
        "Consumer Research",
        "Journalism",
        "UX Research",
    }


def test_soft_skill_vocabulary_stays_small_enough_for_a_dropdown(content_dir):
    """FR-903b — an unranked list of hundreds gets nothing tagged. The soft
    vocabulary is shared on purpose; fragmenting it defeats the ranking."""
    bundle = load_content(content_dir)
    soft = {name for (name, kind) in bundle.skills if kind == SkillType.SOFT}
    assert len(soft) <= 30, f"soft skill vocabulary has grown to {len(soft)}"


def test_ranked_skills_preserve_their_order(content_dir):
    bundle = load_content(content_dir)
    data_analytics = next(r for r in bundle.roles if r.name == "Data Analytics")
    assert data_analytics.hard_skills[0] == "SQL"
    assert data_analytics.aliases[0] == "data analyst"


def test_slugs_are_unique_and_stable(content_dir):
    bundle = load_content(content_dir)
    slugs = [r.slug for r in bundle.roles]
    assert len(set(slugs)) == len(slugs)
    assert slugify("Mechanical / Civil / Chemical") == "mechanical-civil-chemical"


def test_slug_lock_matches_the_content(content_dir):
    """A changed slug orphans every programme and score pointing at it, so it
    must show up as a reviewable diff."""
    bundle = load_content(content_dir)
    locked = read_slug_lock(content_dir)
    assert locked is not None, "content/slugs.lock should be committed"
    assert check_slug_lock(bundle, content_dir) == []


def test_a_renamed_role_in_one_file_fails_the_join(tmp_path, content_dir):
    """The failure mode this prevents: a role renamed in rubrics.md but not in
    deliverables.md would silently lose its deliverable."""
    for name in ("rubrics.md", "resources.md", "deliverables.md", "skills.md"):
        (tmp_path / name).write_text(
            (content_dir / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    broken = (tmp_path / "deliverables.md").read_text(encoding="utf-8")
    broken = broken.replace("| Data Analytics |", "| Data Analysis |", 1)
    (tmp_path / "deliverables.md").write_text(broken, encoding="utf-8")

    with pytest.raises(SeedError, match="do not match across"):
        load_content(tmp_path)


def test_a_malformed_table_row_names_the_line(tmp_path, content_dir):
    """Parsers raise rather than skipping: a silently dropped role would mean a
    programme that simply does not exist."""
    source = (content_dir / "rubrics.md").read_text(encoding="utf-8")
    broken = source.replace(
        "| **5** Cleaning decisions documented.",
        "| Cleaning decisions documented.",
        1,
    )
    path = tmp_path / "rubrics.md"
    path.write_text(broken, encoding="utf-8")

    with pytest.raises(ContentError, match="anchor cell must start with"):
        parse_rubrics(path)


def test_seeding_is_idempotent(session, content_dir):
    first = seed_all(session, content_dir)
    assert first.roles_created == EXPECTED_ROLES
    assert first.templates_written == EXPECTED_ROLES

    second = seed_all(session, content_dir)
    assert second.roles_created == 0
    assert second.roles_updated == EXPECTED_ROLES
    assert second.skills_created == 0
    assert second.sources_created == 0

    assert session.query(Role).count() == EXPECTED_ROLES
    assert session.query(RoleTemplate).count() == EXPECTED_ROLES


def test_seeded_sources_are_unverified_with_no_url(session, content_dir):
    """The resource map names sources without URLs. Marking them verified would
    be a lie, and Milestone 0's real work is filling them in."""
    seed_all(session, content_dir)
    sources = list(session.scalars(select(DataPackResource)))

    assert sources
    assert all(s.verification_status == VerificationStatus.UNVERIFIED for s in sources)
    assert all(s.url_or_storage_key is None for s in sources)


def test_every_ranked_skill_resolves_to_a_skill_row(session, content_dir):
    seed_all(session, content_dir)
    names = {s.name for s in session.scalars(select(Skill))}

    for template in session.scalars(select(RoleTemplate)):
        for skill in template.ranked_hard_skills + template.ranked_soft_skills:
            assert skill in names, f"{skill!r} is ranked but not in the taxonomy"


def test_role_aliases_are_searchable(session, content_dir):
    """FR-043 — a company searching 'BI' should land on Data Analytics rather
    than creating a near-duplicate."""
    seed_all(session, content_dir)
    role = session.scalar(select(Role).where(Role.slug == "data-analytics"))
    assert "BI" in role.aliases
    assert "business intelligence" in role.aliases
