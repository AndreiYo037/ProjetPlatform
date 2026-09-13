"""projet-seed — parse, validate and load content/ into the database.

projet-seed --check     parse and validate only, writes nothing (runs in CI)
projet-seed             load, idempotently
projet-seed --write-lock  refresh content/slugs.lock after a deliberate rename
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from projet.config import get_settings
from projet.db import get_sessionmaker
from projet.seeds.loader import (
    SeedError,
    check_slug_lock,
    load_content,
    seed_all,
    write_slug_lock,
)
from projet.seeds.parsers import ContentError


def _report_readiness(bundle) -> None:
    unverified = sum(len(r.public_sources) for r in bundle.roles)
    at_risk = [r.name for r in bundle.roles if r.delivery_risk_note]
    print(f"  roles              {len(bundle.roles)}")
    print(f"  clusters           {len({r.cluster for r in bundle.roles})}")
    print(f"  skills             {len(bundle.skills)}")
    print(f"  source entries     {unverified} (all unverified — see projet-verify-sources)")

    links = sum(len(entry.capabilities) for entry in bundle.skill_capabilities)
    print(f"  capabilities       {len(bundle.capabilities)} ({links} skill links)")
    # The spread is the review signal for derived content: an axis almost
    # nothing maps onto is a word in a table, and one almost everything maps
    # onto carries no signal on a profile.
    per_axis: dict[str, int] = {c.name: 0 for c in bundle.capabilities}
    for entry in bundle.skill_capabilities:
        for name in entry.capabilities:
            per_axis[name] += 1
    spread = ", ".join(f"{name} {count}" for name, count in sorted(per_axis.items()))
    print(f"  mapped per axis    {spread}")

    if at_risk:
        print(f"  tight at 6 days    {', '.join(at_risk)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the Projet role taxonomy.")
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    parser.add_argument("--write-lock", action="store_true", help="refresh content/slugs.lock")
    parser.add_argument("--content-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    content_dir = args.content_dir or get_settings().content_dir

    try:
        bundle = load_content(content_dir)
    except (SeedError, ContentError) as error:
        print(f"content validation failed:\n{error}", file=sys.stderr)
        return 1

    print(f"parsed {content_dir}:")
    _report_readiness(bundle)

    drift = check_slug_lock(bundle, content_dir)
    if drift:
        print("\nslug lock drift:", file=sys.stderr)
        for problem in drift:
            print(f"  {problem}", file=sys.stderr)
        if not args.write_lock:
            print(
                "\nA changed slug orphans existing programmes and scores. If this is "
                "intended, re-run with --write-lock to record it.",
                file=sys.stderr,
            )
            return 1

    if args.write_lock:
        path = write_slug_lock(bundle, content_dir)
        print(f"\nwrote {path}")

    if args.check:
        print("\ncheck passed; nothing written to the database.")
        return 0

    with get_sessionmaker()() as session:
        report = seed_all(session, content_dir)

    print("\nseeded:")
    for key, value in report.as_dict().items():
        print(f"  {key.replace('_', ' '):<24} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
