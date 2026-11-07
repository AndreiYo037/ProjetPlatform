"""Read-only: the live schedule of the Christmas Together challenge."""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"
SLUG = "christmas-together-2026-queue-management-system"


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
        row = next((r for r in client.get("/programmes").json() if r.get("slug") == SLUG), None)
        if row is None:
            print("!! challenge not found")
            return 1
        for key, value in sorted(row.items()):
            if key.endswith("_at") or "pitch" in key or key in ("status", "onsite"):
                print(f"{key} = {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
