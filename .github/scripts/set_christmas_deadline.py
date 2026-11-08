"""Move the Christmas Together submission deadline to 8 Nov 2026, 16:00 SGT.

Changes only submit_deadline_at. Prints before and after.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"
SLUG = "christmas-together-2026-queue-management-system"
DEADLINE = "2026-11-08T16:00:00+08:00"


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2
    with httpx.Client(base_url=API_BASE, timeout=60) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code}")
            return 1
        existing = next((r for r in client.get("/programmes").json() if r.get("slug") == SLUG), None)
        if existing is None:
            print("!! challenge not found; nothing changed")
            return 1
        print(f"before: submit_deadline_at={existing['submit_deadline_at']} pitch_at={existing['pitch_at']}")
        resp = client.patch(f"/programmes/{existing['id']}", json={"submit_deadline_at": DEADLINE})
        if resp.status_code != 200:
            print(f"!! update failed: {resp.status_code} {resp.text[:300]}")
            return 1
        after = resp.json()
        print(f"after:  submit_deadline_at={after['submit_deadline_at']} pitch_at={after['pitch_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
