"""Read-only: report how many applications exist on each PĒRL challenge.

Needed before deciding how to handle "remove PĒRL's challenge listings" —
the platform refuses to delete a published programme at all, and if any
student has already applied, that constrains the options further. This
script makes no writes.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "maybelsan2801@gmail.com"
SLUGS = ["product-engineer-intern", "medical-clinical-intern", "gtm-intern"]


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2

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
                continue
            apps = client.get(f"/programmes/{row['id']}/applications")
            count = len(apps.json()) if apps.status_code == 200 else "ERROR"
            print(f"{row['title']} ({slug}): status={row['status']} applications={count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
