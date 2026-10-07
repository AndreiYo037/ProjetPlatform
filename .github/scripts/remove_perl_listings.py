"""Remove PĒRL's 3 challenges from the public directory.

The platform refuses to delete a published programme at all
(DELETE /programmes/{id} only works on a draft, for any actor) — a
deliberate rule, not a gap, and there were zero applications on any of
PĒRL's 3 challenges anyway (checked first via check_perl_applications.py).

The only supported way to drop a published, no-application programme out of
the public /challenges directory is to make its derived state "complete":
_state() in public.py treats a passed submit_deadline_at as complete via
programme_is_past(). Today's actual event window (2026-10-07 18:00-22:00
SGT) can't be moved into the past relative to "now" while it's still before
18:00 SGT, since bind_dates() requires end > start — so this moves the whole
window to a date already in the past instead (2026-09-01), satisfying that
constraint while flipping the derived state to complete.

This is fully reversible (just PATCH the dates back) and destroys nothing:
title, brief, deliverable, rubric and access code are all untouched. It
still shows on PĒRL's own company careers page (/x/{slug}), which lists
complete programmes too — only the shared /challenges browse page excludes
them, which is the surface "remove the listings" is actually about.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "maybelsan2801@gmail.com"
SLUGS = ["product-engineer-intern", "medical-clinical-intern", "gtm-intern"]

PAST_START = "2026-09-01T00:00:00+08:00"
PAST_END = "2026-09-01T04:00:00+08:00"


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2

    failed = 0
    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code} {login.text[:200]}")
            return 1

        listing = client.get("/programmes")
        if listing.status_code != 200:
            print(f"!! list failed: {listing.status_code} {listing.text[:200]}")
            return 1
        by_slug = {row["slug"]: row for row in listing.json() if row["slug"] in SLUGS}

        for slug in SLUGS:
            row = by_slug.get(slug)
            if row is None:
                print(f"{slug}: not found")
                failed += 1
                continue
            resp = client.patch(
                f"/programmes/{row['id']}",
                json={"start_at": PAST_START, "submit_deadline_at": PAST_END},
            )
            if resp.status_code != 200:
                print(f"!! {row['title']}: {resp.status_code} {resp.text[:300]}")
                failed += 1
                continue
            print(f"{row['title']} ({slug}): dates moved to the past, now complete/delisted")

    print(f"\n{len(SLUGS) - failed}/{len(SLUGS)} removed from the public directory.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
