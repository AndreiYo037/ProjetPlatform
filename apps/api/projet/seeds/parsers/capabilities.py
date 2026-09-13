"""Parse content/capabilities.md — the universal rollup vocabulary and the
skill → capability map.

Two shapes in one file:
  * '## Capabilities' followed by one table of 'Capability | What it means',
    in display order
  * '## Skill map' followed by any number of 'Skill | Capabilities' tables
    (hard and soft are split into subsections for review, not for the parser)

Everything else in the file is prose and is skipped. Sections are located by
exact heading rather than by position, so reordering the document's commentary
cannot silently change what gets seeded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from projet.seeds.parsers.common import (
    ContentError,
    parse_table_rows,
    read_lines,
    split_list,
    strip_markdown,
)

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CAPABILITIES_HEADING = "Capabilities"
_SKILL_MAP_HEADING = "Skill map"


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    summary: str
    sort_order: int


@dataclass(frozen=True)
class SkillCapabilities:
    skill: str
    capabilities: list[str]


@dataclass(frozen=True)
class CapabilityContent:
    capabilities: list[CapabilitySpec]
    skill_map: list[SkillCapabilities]


def _section_bounds(lines: list[str], path: Path, title: str) -> tuple[int, int]:
    """Line range of the '## <title>' section, ending at the next heading of the
    same or higher level. Subsections inside it are included."""
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        match = _HEADING.match(line)
        if not match:
            continue
        depth, heading = len(match.group(1)), strip_markdown(match.group(2))
        if start is None:
            if depth == 2 and heading == title:
                start, level = index + 1, depth
            continue
        if depth <= level:
            return start, index
    if start is None:
        raise ContentError(path, 0, f"missing '## {title}' section")
    return start, len(lines)


def _parse_capabilities(lines: list[str], path: Path) -> list[CapabilitySpec]:
    start, end = _section_bounds(lines, path, _CAPABILITIES_HEADING)
    rows, _ = parse_table_rows(lines[start:end], 0, path, expected_columns=2)
    specs: list[CapabilitySpec] = []
    seen: set[str] = set()
    for order, row in enumerate(rows, start=1):
        line_no = start + row.line_no
        name = strip_markdown(row.cells[0])
        summary = strip_markdown(row.cells[1])
        if not name:
            raise ContentError(path, line_no, "empty capability name")
        if not summary:
            raise ContentError(path, line_no, f"capability {name!r} has no description")
        if name in seen:
            raise ContentError(path, line_no, f"duplicate capability {name!r}")
        seen.add(name)
        specs.append(CapabilitySpec(name=name, summary=summary, sort_order=order))
    if not specs:
        raise ContentError(path, start, "no capabilities defined")
    return specs


def _parse_skill_map(lines: list[str], path: Path) -> list[SkillCapabilities]:
    start, end = _section_bounds(lines, path, _SKILL_MAP_HEADING)
    section = lines[start:end]
    entries: list[SkillCapabilities] = []
    seen: set[str] = set()
    index = 0

    while index < len(section):
        if not section[index].strip().startswith("|"):
            index += 1
            continue
        rows, index = parse_table_rows(section, index, path, expected_columns=2)
        for row in rows:
            line_no = start + row.line_no
            skill = strip_markdown(row.cells[0])
            capabilities = split_list(strip_markdown(row.cells[1]))
            if not skill:
                raise ContentError(path, line_no, "empty skill name")
            if not capabilities:
                raise ContentError(path, line_no, f"skill {skill!r} maps to no capability")
            if len(set(capabilities)) != len(capabilities):
                raise ContentError(path, line_no, f"skill {skill!r} repeats a capability")
            if skill in seen:
                raise ContentError(path, line_no, f"duplicate skill row {skill!r}")
            seen.add(skill)
            entries.append(SkillCapabilities(skill=skill, capabilities=capabilities))

    if not entries:
        raise ContentError(path, start, "no skill rows found")
    return entries


def parse_capabilities(path: Path) -> CapabilityContent:
    lines = read_lines(path)
    capabilities = _parse_capabilities(lines, path)
    skill_map = _parse_skill_map(lines, path)

    known = {spec.name for spec in capabilities}
    for entry in skill_map:
        unknown = [name for name in entry.capabilities if name not in known]
        if unknown:
            # A typo here would otherwise seed a capability nobody defined and
            # quietly split a profile axis in two.
            raise ContentError(
                path,
                0,
                f"skill {entry.skill!r} names undefined capabilities: {', '.join(sorted(unknown))}",
            )

    return CapabilityContent(capabilities=capabilities, skill_map=skill_map)
