"""Parse content/resources.md.

Four columns per role: public resources, what the company could provide (tagged
[E]/[M]/[H]), and the student tool stack. The ask tags are the whole point of
the column — FR-042's friction tiers come straight off them.
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
    split_comma_list,
    split_list,
    strip_markdown,
)

_CLUSTER_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_ASK_TAG = re.compile(r"^\[([EMH])\]\s*(.+)$")
_BASELINE_ASKS = re.compile(r"^\*\*Always asked of the company \[E\]:\*\*\s*(.+)$")
_BASELINE_PROVIDED = re.compile(r"^\*\*Always provided by you:\*\*\s*(.+)$")
_BASELINE_STACK = re.compile(r"^\*\*Baseline student stack \(all free\):\*\*\s*(.+)$")


@dataclass
class RoleResources:
    role: str
    cluster: str
    public_sources: list[str] = field(default_factory=list)
    asks_easy: list[str] = field(default_factory=list)
    asks_moderate: list[str] = field(default_factory=list)
    asks_hard: list[str] = field(default_factory=list)
    student_tools: list[str] = field(default_factory=list)


@dataclass
class ResourcesDocument:
    roles: list[RoleResources]
    baseline_provided: list[str]
    baseline_asks: list[str]
    baseline_student_stack: list[str]


def _route_asks(cell: str, path: Path, line_no: int, target: RoleResources) -> None:
    for item in split_list(cell):
        match = _ASK_TAG.match(item)
        if not match:
            raise ContentError(
                path,
                line_no,
                f"company ask must be tagged [E], [M] or [H]: {item[:60]!r}",
            )
        tier, text = match.group(1), match.group(2).strip()
        # The hard tier's wording matters — "never ask" is guidance to the
        # person running the sale, so it is preserved verbatim.
        if tier == "E":
            target.asks_easy.append(text)
        elif tier == "M":
            target.asks_moderate.append(text)
        else:
            target.asks_hard.append(text)


def parse_resources(path: Path) -> ResourcesDocument:
    lines = read_lines(path)
    roles: list[RoleResources] = []
    cluster: str | None = None
    provided: list[str] = []
    asks: list[str] = []
    stack: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not provided:
            match = _BASELINE_PROVIDED.match(stripped)
            if match:
                provided = split_comma_list(strip_markdown(match.group(1)).rstrip("."))
        if not asks:
            match = _BASELINE_ASKS.match(stripped)
            if match:
                asks = split_comma_list(strip_markdown(match.group(1)).rstrip("."))
        if not stack:
            match = _BASELINE_STACK.match(stripped)
            if match:
                stack = split_list(strip_markdown(match.group(1)).rstrip("."))

        cluster_match = _CLUSTER_HEADING.match(line)
        if cluster_match:
            candidate = strip_markdown(cluster_match.group(1))
            cluster = candidate if candidate in CLUSTERS else None
            index += 1
            continue

        if cluster and stripped.startswith("|"):
            rows, index = parse_table_rows(lines, index, path, expected_columns=4)
            for row in rows:
                role = strip_markdown(row.cells[0])
                if not role:
                    raise ContentError(path, row.line_no, "empty role cell")
                entry = RoleResources(
                    role=role,
                    cluster=cluster,
                    public_sources=split_comma_list(strip_markdown(row.cells[1])),
                    student_tools=split_comma_list(strip_markdown(row.cells[3])),
                )
                _route_asks(row.cells[2], path, row.line_no, entry)
                roles.append(entry)
            continue

        index += 1

    return ResourcesDocument(
        roles=roles,
        baseline_provided=provided,
        baseline_asks=asks,
        baseline_student_stack=stack,
    )
