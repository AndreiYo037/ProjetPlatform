"""Read-only: participants and Telegram handles per Beans&Beats challenge.

Signs in as the Beans&Beats company account (SEED_PASSWORD secret) and prints,
for each of its challenges, every seated participant with their Telegram
handle and whether they have submitted. Makes no writes.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"


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
        for row in client.get("/programmes").json():
            cards = client.get(f"/programmes/{row['id']}/submissions").json()
            done = [c for c in cards if c.get("submitted_at")]
            print(f"\nCHALLENGE | {row['title']} | status {row['status']}")
            print(f"COUNT | {len(cards)} participants, {len(done)} submitted")
            for c in sorted(cards, key=lambda c: c["name"].lower()):
                mark = "submitted" if c.get("submitted_at") else "-"
                print(f"  {c['name']} | telegram: {c.get('telegram_handle') or '(none)'} | {mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
