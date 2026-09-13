"""Seed the taxonomy from content/.

The three supplied documents are cross-cutting: each covers all 75 roles for one
aspect, rather than one file per role. So the loader joins them on role name and
refuses to seed unless every role appears in every document. That join is where
drift would otherwise creep in silently — a role renamed in rubrics.md but not
in deliverables.md would simply lose its deliverable.

capabilities.md joins the same way, on skill name rather than role name, and is
held to the same standard: every skill the roles rank must map onto at least one
capability, or the seed refuses to run.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.config import get_settings
from projet.models import (
    Capability,
    DataPackResource,
    Role,
    RoleTemplate,
    Skill,
    SkillCapability,
)
from projet.models.enums import Provenance, SkillStatus, SkillType, VerificationStatus
from projet.seeds.parsers import (
    CLUSTERS,
    parse_capabilities,
    parse_deliverables,
    parse_resources,
    parse_rubrics,
    parse_skills,
    parse_universal_rubric,
)
from projet.seeds.parsers.capabilities import CapabilitySpec, SkillCapabilities
from projet.seeds.parsers.common import slugify
from projet.seeds.parsers.rubrics import CriterionSpec

SLUGS_LOCK = "slugs.lock"


class SeedError(RuntimeError):
    pass


@dataclass
class RoleSeed:
    name: str
    cluster: str
    slug: str
    sort_order: int
    aliases: list[str]
    deliverable: str
    public_sources: list[str]
    student_tools: list[str]
    asks_easy: list[str]
    asks_moderate: list[str]
    asks_hard: list[str]
    slot2: CriterionSpec
    slot3: CriterionSpec
    hard_skills: list[str]
    soft_skills: list[str]
    delivery_risk_note: str | None = None


@dataclass
class ContentBundle:
    roles: list[RoleSeed]
    universal_rubric: list[CriterionSpec]
    universal_memo: str | None
    capabilities: list[CapabilitySpec] = field(default_factory=list)
    skill_capabilities: list[SkillCapabilities] = field(default_factory=list)
    baseline_provided: list[str] = field(default_factory=list)
    baseline_asks: list[str] = field(default_factory=list)
    baseline_student_stack: list[str] = field(default_factory=list)

    @property
    def skills(self) -> dict[tuple[str, SkillType], None]:
        seen: dict[tuple[str, SkillType], None] = {}
        for role in self.roles:
            for name in role.hard_skills:
                seen[(name, SkillType.HARD)] = None
            for name in role.soft_skills:
                seen[(name, SkillType.SOFT)] = None
        return seen


def load_content(content_dir: Path | None = None) -> ContentBundle:
    """Parse and join all four documents. Raises SeedError on any mismatch."""
    root = Path(content_dir or get_settings().content_dir)

    rubrics = parse_rubrics(root / "rubrics.md")
    universal = parse_universal_rubric(root / "rubrics.md")
    deliverables_doc = parse_deliverables(root / "deliverables.md")
    resources_doc = parse_resources(root / "resources.md")
    skills = parse_skills(root / "skills.md")
    capabilities = parse_capabilities(root / "capabilities.md")

    by_name: dict[str, dict[str, Any]] = {
        "rubrics.md": {r.role: r for r in rubrics},
        "deliverables.md": {d.role: d for d in deliverables_doc.deliverables},
        "resources.md": {r.role: r for r in resources_doc.roles},
        "skills.md": {s.role: s for s in skills},
    }
    _assert_complete_join(by_name)
    _assert_clusters_agree(by_name)

    at_risk = set(deliverables_doc.at_risk_roles)
    seeds: list[RoleSeed] = []
    for order, rubric in enumerate(rubrics):
        name = rubric.role
        deliverable = by_name["deliverables.md"][name]
        resources = by_name["resources.md"][name]
        role_skills = by_name["skills.md"][name]
        seeds.append(
            RoleSeed(
                name=name,
                cluster=rubric.cluster,
                slug=slugify(name),
                sort_order=order,
                aliases=role_skills.aliases,
                deliverable=deliverable.deliverable,
                public_sources=resources.public_sources,
                student_tools=resources.student_tools,
                asks_easy=resources.asks_easy,
                asks_moderate=resources.asks_moderate,
                asks_hard=resources.asks_hard,
                slot2=rubric.slot2,
                slot3=rubric.slot3,
                hard_skills=role_skills.hard_skills,
                soft_skills=role_skills.soft_skills,
                delivery_risk_note=(
                    deliverables_doc.delivery_risk_note if name in at_risk else None
                ),
            )
        )

    _assert_unique_slugs(seeds)
    bundle_skills = {name for seed in seeds for name in seed.hard_skills + seed.soft_skills}
    _assert_capabilities_cover(bundle_skills, capabilities.skill_map)

    return ContentBundle(
        roles=seeds,
        universal_rubric=universal,
        universal_memo=deliverables_doc.universal_memo,
        capabilities=capabilities.capabilities,
        skill_capabilities=capabilities.skill_map,
        baseline_provided=resources_doc.baseline_provided,
        baseline_asks=resources_doc.baseline_asks,
        baseline_student_stack=resources_doc.baseline_student_stack,
    )


def _assert_complete_join(by_name: dict[str, dict[str, Any]]) -> None:
    everywhere = set.union(*(set(d) for d in by_name.values()))
    problems: list[str] = []
    for filename, mapping in by_name.items():
        missing = sorted(everywhere - set(mapping))
        if missing:
            problems.append(f"  {filename} is missing: {', '.join(missing)}")
    if problems:
        raise SeedError(
            "role names do not match across the content documents.\n"
            + "\n".join(problems)
            + "\n\nEvery role must appear in all four files under exactly the same name. "
            "If you renamed a role, rename it everywhere."
        )


def _assert_clusters_agree(by_name: dict[str, dict[str, Any]]) -> None:
    problems = []
    reference = by_name["rubrics.md"]
    for filename, mapping in by_name.items():
        if filename == "rubrics.md":
            continue
        for role, entry in mapping.items():
            expected = reference[role].cluster
            if entry.cluster != expected:
                problems.append(
                    f"  {role!r}: rubrics.md says {expected!r}, {filename} says {entry.cluster!r}"
                )
    if problems:
        raise SeedError("cluster assignments disagree:\n" + "\n".join(problems))

    unknown = {r.cluster for r in reference.values()} - set(CLUSTERS)
    if unknown:
        raise SeedError(f"unknown clusters: {sorted(unknown)}")


def _assert_capabilities_cover(skill_names: set[str], skill_map: list[SkillCapabilities]) -> None:
    """Both directions, because both failures are silent.

    A skill with no capability never appears on a profile — the rollup simply
    has nothing to join through, and nobody notices until someone asks why a
    participant's Investigation axis is thin. A capability row for a skill that
    no longer exists means capabilities.md is stale against skills.md, which is
    how the two drift apart.
    """
    mapped = {entry.skill for entry in skill_map}
    problems = []
    unmapped = sorted(skill_names - mapped)
    if unmapped:
        problems.append(
            "  skills.md skills with no capability in capabilities.md: " + ", ".join(unmapped)
        )
    orphaned = sorted(mapped - skill_names)
    if orphaned:
        problems.append(
            "  capabilities.md maps skills that are not in skills.md: " + ", ".join(orphaned)
        )
    if problems:
        raise SeedError(
            "the capability map and the skills taxonomy disagree.\n"
            + "\n".join(problems)
            + "\n\nEvery skill must map to at least one capability: an unmapped skill "
            "is invisible on a profile."
        )


def _assert_unique_slugs(seeds: list[RoleSeed]) -> None:
    seen: dict[str, str] = {}
    for seed in seeds:
        if seed.slug in seen:
            raise SeedError(
                f"slug collision: {seed.name!r} and {seen[seed.slug]!r} both slugify "
                f"to {seed.slug!r}"
            )
        seen[seed.slug] = seed.name


# -- slug lock ---------------------------------------------------------------


def slug_map(bundle: ContentBundle) -> dict[str, str]:
    return {seed.name: seed.slug for seed in bundle.roles}


def read_slug_lock(content_dir: Path | None = None) -> dict[str, str] | None:
    path = Path(content_dir or get_settings().content_dir) / SLUGS_LOCK
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_slug_lock(bundle: ContentBundle, content_dir: Path | None = None) -> Path:
    path = Path(content_dir or get_settings().content_dir) / SLUGS_LOCK
    path.write_text(
        json.dumps(slug_map(bundle), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def check_slug_lock(bundle: ContentBundle, content_dir: Path | None = None) -> list[str]:
    """Report drift between the content and the committed lock.

    A changed slug orphans every Programme, Score and ProfileSkill pointing at
    the old one, so it should be a reviewable diff rather than a surprise.
    """
    locked = read_slug_lock(content_dir)
    if locked is None:
        return []
    current = slug_map(bundle)
    problems = []
    for name, slug in locked.items():
        if name not in current:
            problems.append(f"role {name!r} (slug {slug!r}) is no longer in the content")
        elif current[name] != slug:
            problems.append(f"role {name!r} slug changed: {slug!r} -> {current[name]!r}")
    for name, slug in current.items():
        if name not in locked:
            problems.append(f"new role {name!r} (slug {slug!r})")
    return problems


# -- seeding -----------------------------------------------------------------


@dataclass
class SeedReport:
    roles_created: int = 0
    roles_updated: int = 0
    templates_written: int = 0
    skills_created: int = 0
    capabilities_created: int = 0
    capability_links_created: int = 0
    sources_created: int = 0

    def as_dict(self) -> dict:
        return self.__dict__


def seed_skills(session: Session, bundle: ContentBundle, report: SeedReport) -> dict[str, Skill]:
    existing = {s.name: s for s in session.scalars(select(Skill))}
    for name, skill_type in bundle.skills:
        skill = existing.get(name)
        if skill is None:
            skill = Skill(
                name=name,
                slug=slugify(name),
                type=skill_type,
                aliases=[],
                status=SkillStatus.CANONICAL,
            )
            session.add(skill)
            existing[name] = skill
            report.skills_created += 1
        elif skill.type != skill_type:
            raise SeedError(
                f"skill {name!r} appears as both {skill.type.value} and {skill_type.value}; "
                "a name means one thing or the other"
            )
    session.flush()
    return existing


def seed_capabilities(
    session: Session,
    bundle: ContentBundle,
    skills: dict[str, Skill],
    report: SeedReport,
) -> None:
    """Upsert the capability vocabulary and the skill links, keyed on name.

    Links are additive on re-run and are pruned when the content drops one, so
    a re-mapped skill does not keep rolling up onto the axis it was moved off.
    """
    existing = {c.name: c for c in session.scalars(select(Capability))}
    for spec in bundle.capabilities:
        capability = existing.get(spec.name)
        if capability is None:
            capability = Capability(name=spec.name, slug=slugify(spec.name))
            session.add(capability)
            existing[spec.name] = capability
            report.capabilities_created += 1
        capability.summary = spec.summary
        capability.sort_order = spec.sort_order
    session.flush()

    wanted: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for entry in bundle.skill_capabilities:
        skill = skills.get(entry.skill)
        if skill is None:
            # _assert_capabilities_cover already rejects this at parse time; the
            # guard is here so a direct seed_capabilities() call cannot skip it.
            raise SeedError(
                f"capability map names skill {entry.skill!r}, which is not in the taxonomy"
            )
        for name in entry.capabilities:
            wanted.add((skill.id, existing[name].id))

    present = {
        (link.skill_id, link.capability_id) for link in session.scalars(select(SkillCapability))
    }
    for skill_id, capability_id in sorted(wanted - present):
        session.add(SkillCapability(skill_id=skill_id, capability_id=capability_id))
        report.capability_links_created += 1
    for skill_id, capability_id in present - wanted:
        link = session.get(SkillCapability, (skill_id, capability_id))
        if link is not None:
            session.delete(link)
    session.flush()


def seed_roles(session: Session, bundle: ContentBundle, report: SeedReport) -> None:
    skills = seed_skills(session, bundle, report)
    _assert_skills_resolve(bundle, skills)
    seed_capabilities(session, bundle, skills, report)

    existing = {r.slug: r for r in session.scalars(select(Role))}
    for seed in bundle.roles:
        role = existing.get(seed.slug)
        if role is None:
            role = Role(slug=seed.slug)
            session.add(role)
            report.roles_created += 1
        else:
            report.roles_updated += 1

        role.name = seed.name
        role.cluster = seed.cluster
        role.aliases = seed.aliases
        role.sort_order = seed.sort_order
        role.is_active = True
        session.flush()

        template = session.get(RoleTemplate, role.id)
        if template is None:
            template = RoleTemplate(role_id=role.id)
            session.add(template)
        template.default_deliverable = seed.deliverable
        template.public_sources = [
            {"label": label, "verification_status": VerificationStatus.UNVERIFIED.value}
            for label in seed.public_sources
        ]
        template.student_tools = seed.student_tools
        template.asks_easy = seed.asks_easy
        template.asks_moderate = seed.asks_moderate
        template.asks_hard = seed.asks_hard
        template.rubric_slot2_name = seed.slot2.name
        template.rubric_slot2_anchor_5 = seed.slot2.anchor_5
        template.rubric_slot2_anchor_3 = seed.slot2.anchor_3
        template.rubric_slot2_anchor_1 = seed.slot2.anchor_1
        template.rubric_slot3_name = seed.slot3.name
        template.rubric_slot3_anchor_5 = seed.slot3.anchor_5
        template.rubric_slot3_anchor_3 = seed.slot3.anchor_3
        template.rubric_slot3_anchor_1 = seed.slot3.anchor_1
        template.ranked_hard_skills = seed.hard_skills
        template.ranked_soft_skills = seed.soft_skills
        template.delivery_risk_note = seed.delivery_risk_note
        report.templates_written += 1

        _seed_registry_sources(session, role, seed, report)

    session.flush()


def _seed_registry_sources(
    session: Session, role: Role, seed: RoleSeed, report: SeedReport
) -> None:
    """Registry entries per role, seeded unverified.

    The resource map names sources ("SingStat", "LTA DataMall") without URLs, so
    url_or_storage_key stays null until projet-verify-sources has something to
    fetch. Milestone 0's real work is filling these in.
    """
    existing = {
        r.label
        for r in session.scalars(
            select(DataPackResource).where(DataPackResource.role_id == role.id)
        )
    }
    for label in seed.public_sources:
        if label in existing:
            continue
        session.add(
            DataPackResource(
                role_id=role.id,
                label=label,
                provenance=Provenance.PUBLIC,
                verification_status=VerificationStatus.UNVERIFIED,
            )
        )
        report.sources_created += 1


def _assert_skills_resolve(bundle: ContentBundle, skills: dict[str, Skill]) -> None:
    missing = []
    for role in bundle.roles:
        for name in role.hard_skills + role.soft_skills:
            if name not in skills:
                missing.append(f"{role.name}: {name}")
    if missing:
        raise SeedError("ranked skills do not resolve:\n  " + "\n  ".join(missing))


def seed_all(session: Session, content_dir: Path | None = None) -> SeedReport:
    bundle = load_content(content_dir)
    report = SeedReport()
    seed_roles(session, bundle, report)
    session.commit()
    return report
