"""Read-only: count participant submissions across all Startup Shuffle
challenges, submitted since the event started (2026-10-07T18:00 SGT).

Makes no writes. Logs in as each company (same SEED_PASSWORD used for every
company account this event), lists their programmes, and for each one pulls
the judging day's submission cards (GET /programmes/{id}/submissions) to
count how many participants have a submitted_at at or after the cutoff.
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

    total_since_cutoff = 0
    total_all_time = 0

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
                    print(
                        f"  !! {row['title']} ({row['slug']}): could not fetch submissions "
                        f"({cards_resp.status_code})"
                    )
                    continue
                cards = cards_resp.json()
                since_cutoff = 0
                all_time = 0
                for card in cards:
                    submitted_at = _parse(card.get("submitted_at"))
                    if submitted_at is None:
                        continue
                    all_time += 1
                    if submitted_at >= CUTOFF:
                        since_cutoff += 1
                total_since_cutoff += since_cutoff
                total_all_time += all_time
                print(
                    f"{row['title']} ({row['slug']}): {since_cutoff} since 6pm "
                    f"(of {all_time} total, {len(cards)} participants)"
                )

    print(f"\nTOTAL since 2026-10-07 18:00 SGT: {total_since_cutoff}")
    print(f"TOTAL all time: {total_all_time}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
