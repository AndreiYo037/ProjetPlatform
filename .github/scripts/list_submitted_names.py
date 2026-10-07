"""Read-only: list the names of participants who have submitted on each
Startup Shuffle challenge, since the event started (2026-10-07T18:00 SGT).

Companion to check_submissions_since_event_start.py — same aggregation, but
prints names instead of just counts. Makes no writes.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")

CUTOFF = datetime(2026, 10, 7, 10, 0, 0, tzinfo=timezone.utc)  # 2026-10-07T18:00 SGT

COMPANY_EMAILS = [
    "maybelsan2801@gmail.com",
    "kayhngquek@gmail.com",
    "verrell88.kc@gmail.com",
    "e1356491@u.nus.edu",
    "rija.hilmi@gmail.com",
    "sindhu@snowball.day",
    "hello@thirdspacesmarketing.com",
    "eugenewang1227@gmail.com",
    "faithlum@u.nus.edu",
    "zqingyuan@flowcoffee.sg",
    "royomaterial@royomaterial.com",
]


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2

    total = 0
    for email in COMPANY_EMAILS:
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code} {login.text[:200]}")
                continue

            listing = client.get("/programmes")
            if listing.status_code != 200:
                print(f"!! could not list programmes for {email}: {listing.status_code}")
                continue

            for row in listing.json():
                cards_resp = client.get(f"/programmes/{row['id']}/submissions")
                if cards_resp.status_code != 200:
                    continue
                names = [
                    card["name"]
                    for card in cards_resp.json()
                    if (submitted := _parse(card.get("submitted_at"))) and submitted >= CUTOFF
                ]
                if not names:
                    continue
                total += len(names)
                print(f"\n{row['title']} ({row['slug']}):")
                for name in names:
                    print(f"  - {name}")

    print(f"\nTOTAL: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
