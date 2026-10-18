"""Read-only: which shipped features is production actually serving?

Reads the live OpenAPI schema and looks for the fields each feature added.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")

# label -> (json path marker that must appear in the live schema)
CHECKS = [
    ("submission memo", '"/me/submission/memo"'),
    ("pitch mode (online/onsite)", '"/me/submission/pitch-mode"'),
    ("judge's own score override", '"manual_total"'),
    ("hide unsubmitted (own_score flag)", '"own_score"'),
]


def main() -> int:
    raw = httpx.get(f"{API_BASE}/openapi.json", timeout=60).text
    missing = []
    for label, marker in CHECKS:
        live = marker in raw
        print(f"{'live    ' if live else 'NOT live'} | {label}")
        if not live:
            missing.append(label)
    print(f"\n{len(CHECKS) - len(missing)}/{len(CHECKS)} live.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
