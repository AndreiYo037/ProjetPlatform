"""Open the Christmas Together challenge today.

On-site challenges open applying at the start time, so this moves start_at to
today (times of day are pinned server-side to 00:00 SGT) and the application
open date with it. Everything else on the challenge is left alone.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"
SLUG = "christmas-together-2026-queue-management-system"


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2
    today = datetime.now(ZoneInfo("Asia/Singapore")).date().isoformat()
    midnight = f"{today}T00:00:00+08:00"
    with httpx.Client(base_url=API_BASE, timeout=60) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code}")
            return 1
        programmes = client.get("/programmes").json()
        existing = next((r for r in programmes if r.get("slug") == SLUG), None)
        if existing is None or existing["delivery_mode"] != "in_person":
            print("!! on-site challenge not found; nothing changed")
            return 1
        print(f"before: start={existing['start_at']} open={existing['applications_open_at']}")
        resp = client.patch(
            f"/programmes/{existing['id']}",
            json={"start_at": midnight, "applications_open_at": midnight},
        )
        if resp.status_code != 200:
            print(f"!! update failed: {resp.status_code} {resp.text[:300]}")
            return 1
        after = resp.json()
        print(f"after:  start={after['start_at']} open={after['applications_open_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
