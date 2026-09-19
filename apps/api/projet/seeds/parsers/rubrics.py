"""Parse content/rubrics.md.

Two shapes in one file:
  * the fixed criteria (slots 1 and 4) in the opening section, as
    '## Slot N — Name' followed by a two-column table of 5/3/1 anchors
  * per role, '### Role Name' followed by a table whose header names slot 2 and
    slot 3 and whose three rows carry the 5/3/1 anchors for both
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from projet.seeds.parsers.common import (
    CLUSTERS,
    ContentError,
    parse_table_rows,
    read_lines,
    strip_markdown,
)

# '| Slot 2 — *What worked and what didn't* |' -> slot number and criterion name
_SLOT_HEADER = re.compile(r"Slot\s*(\d)\s*[—–-]\s*\*?(.+?)\*?\s*$")
# '**5** Eval set includes...' -> band and anchor text
_ANCHOR = re.compile(r"^\*\*([531])\*\*\s*(.*)$", re.DOTALL)
_ROLE_HEADING = re.compile(r"^###\s+(.+?)\s*$")
_CLUSTER_HEADING = re.compile(r"^#\s+(.+?)\s*$")
_SLOT_SECTION = re.compile(r"^##\s+Slot\s*(\d)\s*[—–-]\s*(.+?)\s*$")


@dataclass
class CriterionSpec:
    slot: int
    name: str
    anchor_5: str
    anchor_3: str
    anchor_1: str


@dataclass
class RoleRubric:
    role: str
    cluster: str
    slot2: CriterionSpec
    slot3: CriterionSpec


def _anchor_parts(cell: str, path: Path, line_no: int) -> tuple[str, str]:
    match = _ANCHOR.match(cell.strip())
    if not match:
        raise ContentError(
            path, line_no, f"anchor cell must start with **5**, **3** or **1**: {cell[:60]!r}"
        )
    return match.group(1), strip_markdown(match.group(2))


def parse_universal_rubric(path: Path) -> list[CriterionSpec]:
    """Slots 1 and 4 — the two that do not vary, and the reason a Finance cohort
    can be compared to an ESG cohort at all (FR-072)."""
    lines = read_lines(path)
    specs: list[CriterionSpec] = []
    index = 0

    while index < len(lines):
        match = _SLOT_SECTION.match(lines[index])
        if not match:
            index += 1
            continue
        slot = int(match.group(1))
        name = strip_markdown(match.group(2))
        rows, index = parse_table_rows(lines, index + 1, path, expected_columns=2)
        anchors: dict[str, str] = {}
        for row in rows:
            band, text = _anchor_parts(row.cells[0], path, row.line_no)
            anchors[band] = strip_markdown(row.cells[1]) or text
        missing = {"5", "3", "1"} - anchors.keys()
        if missing:
            raise ContentError(path, index, f"slot {slot} missing anchors {sorted(missing)}")
        specs.append(
            CriterionSpec(
                slot=slot,
                name=name,
                anchor_5=anchors["5"],
                anchor_3=anchors["3"],
                anchor_1=anchors["1"],
            )
        )

    found = {spec.slot for spec in specs}
    if found != {1, 4}:
        raise ContentError(path, 0, f"expected universal slots 1 and 4, found {sorted(found)}")
    return specs


def parse_rubrics(path: Path) -> list[RoleRubric]:
    """Slots 2 and 3, per role."""
    lines = read_lines(path)
    rubrics: list[RoleRubric] = []
    cluster: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]

        cluster_match = _CLUSTER_HEADING.match(line)
        if cluster_match:
            candidate = strip_markdown(cluster_match.group(1))
            # Only whitelisted clusters count; the file's prose sections use the
            # same heading level and must not become roles.
            cluster = candidate if candidate in CLUSTERS else None
            index += 1
            continue

        role_match = _ROLE_HEADING.match(line)
        if not role_match:
            index += 1
            continue
        if cluster is None:
            index += 1
            continue

        role_name = strip_markdown(role_match.group(1))
        header_line = index + 1
        if header_line >= len(lines) or not lines[header_line].strip().startswith("|"):
            raise ContentError(path, header_line + 1, f"role {role_name!r} has no rubric table")

        header_cells = [c.strip() for c in lines[header_line].strip().strip("|").split("|")]
        if len(header_cells) != 2:
            raise ContentError(
                path, header_line + 1, f"role {role_name!r} header must have 2 columns"
            )
        slots = []
        for cell in header_cells:
            slot_match = _SLOT_HEADER.search(cell)
            if not slot_match:
                raise ContentError(path, header_line + 1, f"cannot read slot header: {cell[:60]!r}")
            slots.append((int(slot_match.group(1)), strip_markdown(slot_match.group(2))))
        if [s for s, _ in slots] != [2, 3]:
            raise ContentError(
                path, header_line + 1, f"role {role_name!r} must define slots 2 and 3"
            )

        rows, index = parse_table_rows(lines, header_line, path, expected_columns=2)
        anchors: dict[int, dict[str, str]] = {2: {}, 3: {}}
        for row in rows:
            for column, (slot, _) in enumerate(slots):
                band, text = _anchor_parts(row.cells[column], path, row.line_no)
                anchors[slot][band] = text

        for slot, _ in slots:
            missing = {"5", "3", "1"} - anchors[slot].keys()
            if missing:
                raise ContentError(
                    path,
                    header_line + 1,
                    f"role {role_name!r} slot {slot} missing anchors {sorted(missing)}",
                )

        rubrics.append(
            RoleRubric(
                role=role_name,
                cluster=cluster,
                slot2=CriterionSpec(
                    slot=2,
                    name=slots[0][1],
                    anchor_5=anchors[2]["5"],
                    anchor_3=anchors[2]["3"],
                    anchor_1=anchors[2]["1"],
                ),
                slot3=CriterionSpec(
                    slot=3,
                    name=slots[1][1],
                    anchor_5=anchors[3]["5"],
                    anchor_3=anchors[3]["3"],
                    anchor_1=anchors[3]["1"],
                ),
            )
        )

    return rubrics
