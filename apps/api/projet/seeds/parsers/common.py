"""Shared markdown-table machinery and the cluster whitelist."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# The eleven clusters, whitelisted explicitly. Parsing by "any heading" would
# pull in the prose sections these documents end with — the rubric authoring
# guide, the seeding notes — and turn them into roles.
CLUSTERS = (
    "AI & Data",
    "Engineering & Technical",
    "Product & Design",
    "Business & Strategy",
    "Finance",
    "Marketing, Sales & Media",
    "Consumer & Research",
    "People & Organisation",
    "Legal, Policy & Public",
    "Health & Life Sciences",
    "Sustainability & Industrials",
)

LIST_SEPARATOR = "·"
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


class ContentError(ValueError):
    """Raised with the file and line so a bad row is findable in one look."""

    def __init__(self, path: Path | str, line_no: int, message: str) -> None:
        super().__init__(f"{path}:{line_no}: {message}")
        self.path = str(path)
        self.line_no = line_no


@dataclass(frozen=True)
class TableRow:
    cells: list[str]
    line_no: int


def slugify(value: str) -> str:
    """Deterministic and stable — 'Mechanical / Civil / Chemical' becomes
    'mechanical-civil-chemical'. Snapshotted in content/slugs.lock so a rename
    shows up as a reviewable diff instead of orphaning live data."""
    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode()
    return _SLUG_STRIP.sub("-", ascii_only.lower()).strip("-")


def strip_markdown(value: str) -> str:
    """Remove the emphasis the documents use for readability, keeping the text."""
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"\*(.+?)\*", r"\1", value)
    return value.strip()


def split_list(value: str) -> list[str]:
    """Split a '·'-separated cell, dropping empties."""
    if not value:
        return []
    return [part.strip() for part in value.split(LIST_SEPARATOR) if part.strip()]


def split_comma_list(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def is_separator_row(cells: list[str]) -> bool:
    return all(set(cell.strip()) <= {"-", ":"} and cell.strip() for cell in cells)


def parse_table_rows(
    lines: list[str],
    start: int,
    path: Path | str,
    *,
    expected_columns: int,
) -> tuple[list[TableRow], int]:
    """Read one markdown table starting at `start`.

    Returns the data rows (header and separator dropped) and the index of the
    first line after the table.
    """
    rows: list[TableRow] = []
    index = start
    seen_header = False

    while index < len(lines):
        raw = lines[index].strip()
        if not raw.startswith("|"):
            if rows or seen_header:
                break
            index += 1
            continue

        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) != expected_columns:
            raise ContentError(
                path,
                index + 1,
                f"expected {expected_columns} columns, found {len(cells)}: {raw[:80]!r}",
            )
        if is_separator_row(cells):
            index += 1
            continue
        if not seen_header:
            seen_header = True
            index += 1
            continue

        rows.append(TableRow(cells=cells, line_no=index + 1))
        index += 1

    return rows, index


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise ContentError(path, 0, "content file not found")
    return path.read_text(encoding="utf-8").splitlines()
