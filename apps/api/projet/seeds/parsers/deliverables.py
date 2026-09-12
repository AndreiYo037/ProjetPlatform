"""Parse content/deliverables.md — 'Role | Deliverable' tables per cluster.

The universal memo ("the named artifact plus a half-page memo — what a judge
reads first") is global, not per role, so it is captured once here rather than
repeated seventy-five times.
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

_CLUSTER_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_MEMO_LINE = re.compile(r"^\*\*Universal, every role:\*\*\s*(.+)$")
# "Four roles are tight at this length" — the delivery risk note
_RISK_LINE = re.compile(r"^\*\*Four roles are tight at this length\*\*\s*(.+)$")


@dataclass
class RoleDeliverable:
    role: str
    cluster: str
    deliverable: str


@dataclass
class DeliverablesDocument:
    deliverables: list[RoleDeliverable]
    universal_memo: str | None
    delivery_risk_note: str | None
    at_risk_roles: list[str]


def parse_deliverables(path: Path) -> DeliverablesDocument:
    lines = read_lines(path)
    results: list[RoleDeliverable] = []
    cluster: str | None = None
    memo: str | None = None
    risk_note: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]

        if memo is None:
            memo_match = _MEMO_LINE.match(line.strip())
            if memo_match:
                memo = strip_markdown(memo_match.group(1))

        if risk_note is None:
            risk_match = _RISK_LINE.match(line.strip())
            if risk_match:
                risk_note = strip_markdown(risk_match.group(1))

        cluster_match = _CLUSTER_HEADING.match(line)
        if cluster_match:
            candidate = strip_markdown(cluster_match.group(1))
            cluster = candidate if candidate in CLUSTERS else None
            index += 1
            continue

        if cluster and line.strip().startswith("|"):
            rows, index = parse_table_rows(lines, index, path, expected_columns=2)
            for row in rows:
                role = strip_markdown(row.cells[0])
                deliverable = strip_markdown(row.cells[1])
                if not role or not deliverable:
                    raise ContentError(path, row.line_no, "empty role or deliverable cell")
                results.append(RoleDeliverable(role=role, cluster=cluster, deliverable=deliverable))
            continue

        index += 1

    at_risk = _extract_at_risk(risk_note or "", {r.role for r in results})
    return DeliverablesDocument(
        deliverables=results,
        universal_memo=memo,
        delivery_risk_note=risk_note,
        at_risk_roles=at_risk,
    )


def _extract_at_risk(note: str, known_roles: set[str]) -> list[str]:
    """Pull the named roles out of the 'tight at this length' note.

    Matching against roles the document actually defines means a reworded note
    degrades to an empty list rather than inventing a role that does not exist.
    """
    found = [role for role in known_roles if role and role in note]
    return sorted(found)
