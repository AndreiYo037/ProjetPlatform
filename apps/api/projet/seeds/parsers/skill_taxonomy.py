"""Parse content/skill-taxonomy.md — the platform-wide tag vocabulary.

skills.md ranks a shortlist per role. This file is the rest of the picker:
every name here is offered in search, and names already ranked in skills.md
are written exactly as they appear there so the seed treats them as one skill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from projet.models.enums import SkillType
from projet.seeds.parsers.common import ContentError, read_lines, split_list, strip_markdown

_SECTION = re.compile(r"^##(?!#)\s+(.+?)\s*$")
_SUBSECTION = re.compile(r"^###\s+")
_CAPABILITIES = re.compile(r"^Capabilities:\s*(.+?)\s*$")
_ITEM = re.compile(r"^-\s+(.+?)\s*$")
_SOFT_MARK = re.compile(r"\s+\(soft\)\s*$")


@dataclass(frozen=True)
class TaxonomySkill:
    name: str
    type: SkillType
    capabilities: list[str]
    group: str


def parse_skill_taxonomy(path: Path) -> list[TaxonomySkill]:
    lines = read_lines(path)
    results: list[TaxonomySkill] = []
    seen: set[str] = set()
    group: str | None = None
    skill_type = SkillType.HARD
    capabilities: list[str] = []
    expecting_capabilities = False

    for index, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue

        if _SUBSECTION.match(line):
            continue

        section = _SECTION.match(line)
        if section:
            heading = strip_markdown(section.group(1))
            skill_type = SkillType.SOFT if _SOFT_MARK.search(heading) else SkillType.HARD
            group = _SOFT_MARK.sub("", heading).strip()
            capabilities = []
            expecting_capabilities = True
            continue

        cap = _CAPABILITIES.match(line)
        if cap:
            if group is None:
                raise ContentError(path, index, "capabilities line with no section")
            capabilities = split_list(strip_markdown(cap.group(1)))
            if not capabilities:
                raise ContentError(path, index, f"section {group!r} maps to no capability")
            expecting_capabilities = False
            continue

        item = _ITEM.match(line)
        if item:
            if group is None:
                raise ContentError(path, index, "skill with no section")
            if expecting_capabilities or not capabilities:
                raise ContentError(
                    path, index, f"section {group!r} is missing a Capabilities line"
                )
            name = strip_markdown(item.group(1))
            if not name:
                raise ContentError(path, index, "empty skill name")
            key = name.lower()
            if key in seen:
                raise ContentError(path, index, f"duplicate skill {name!r}")
            seen.add(key)
            results.append(
                TaxonomySkill(
                    name=name,
                    type=skill_type,
                    capabilities=list(capabilities),
                    group=group,
                )
            )

    if not results:
        raise ContentError(path, 0, "no skills found")
    return results
