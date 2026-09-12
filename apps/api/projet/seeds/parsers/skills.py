"""Parse content/skills.md — aliases and the ranked skill lists per role.

Order is meaningful and preserved: it is the order the FR-903b dropdown shows,
and an alphabetical list of hundreds is the failure mode the PRD calls out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from projet.seeds.parsers.common import (
    CLUSTERS,
    ContentError,
    parse_table_rows,
    read_lines,
    split_list,
    strip_markdown,
)

_CLUSTER_HEADING = re.compile(r"^##\s+(.+?)\s*$")


@dataclass
class RoleSkills:
    role: str
    cluster: str
    aliases: list[str] = field(default_factory=list)
    hard_skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)


def parse_skills(path: Path) -> list[RoleSkills]:
    lines = read_lines(path)
    results: list[RoleSkills] = []
    cluster: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]

        cluster_match = _CLUSTER_HEADING.match(line)
        if cluster_match:
            candidate = strip_markdown(cluster_match.group(1))
            cluster = candidate if candidate in CLUSTERS else None
            index += 1
            continue

        if cluster and line.strip().startswith("|"):
            rows, index = parse_table_rows(lines, index, path, expected_columns=4)
            for row in rows:
                role = strip_markdown(row.cells[0])
                hard = split_list(strip_markdown(row.cells[2]))
                soft = split_list(strip_markdown(row.cells[3]))
                if not role:
                    raise ContentError(path, row.line_no, "empty role cell")
                if not hard or not soft:
                    raise ContentError(
                        path,
                        row.line_no,
                        f"role {role!r} needs at least one hard and one soft skill",
                    )
                results.append(
                    RoleSkills(
                        role=role,
                        cluster=cluster,
                        aliases=split_list(strip_markdown(row.cells[1])),
                        hard_skills=hard,
                        soft_skills=soft,
                    )
                )
            continue

        index += 1

    return results
