"""Strict parsers for the canonical markdown in content/.

Every parser raises ContentError naming file and line rather than skipping a row
it cannot read. A role silently dropped from the taxonomy is worse than a failed
seed run: the programme it backs would simply not exist.
"""

from projet.seeds.parsers.capabilities import parse_capabilities
from projet.seeds.parsers.common import (
    CLUSTERS,
    ContentError,
    parse_table_rows,
    split_list,
)
from projet.seeds.parsers.deliverables import parse_deliverables
from projet.seeds.parsers.resources import parse_resources
from projet.seeds.parsers.rubrics import parse_rubrics, parse_universal_rubric
from projet.seeds.parsers.skills import parse_skills

__all__ = [
    "CLUSTERS",
    "ContentError",
    "parse_capabilities",
    "parse_deliverables",
    "parse_resources",
    "parse_rubrics",
    "parse_skills",
    "parse_table_rows",
    "parse_universal_rubric",
    "split_list",
]
