"""Read-only: participants per Hack n Hire track (challenge).

Logs in as each of the four company accounts and, for each Hack n Hire
challenge, counts seated participants and how many have submitted.
COMPANY_PASSWORD is a workflow input. Makes no writes.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2

    by_email: dict[str, list[dict]] = {}
    for item in CHALLENGES:
        by_email.setdefault(item["email"], []).append(item)

    rows: list[tuple[str, int, int, int, int]] = []
    people: set[str] = set()
    modes = {"online": 0, "onsite": 0, "not chosen": 0}
    for email, items in by_email.items():
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                return 1
            programmes = {r["slug"]: r for r in client.get("/programmes").json()}
            for item in items:
                row = programmes.get(item["slug"])
                if row is None:
                    print(f"!! {item['slug']} not found")
                    return 1
                cards = client.get(f"/programmes/{row['id']}/submissions").json()
                for c in cards:
                    key = (c.get("contact_email") or c.get("google_email") or c["name"]).lower()
                    people.add(key)
                done = [c for c in cards if c.get("submitted_at")]
                submitted = len(done)
                for c in done:
                    modes[c.get("pitch_mode") or "not chosen"] += 1
                print(f"SUBMITTED | {item['title'][:40]} | " + "; ".join(sorted(c["name"] for c in done)))
                print(f"ALL | {item['title'][:40]} | " + "; ".join(sorted(c["name"] for c in cards)))
                print(f"MODE | {item['title'][:30]} | " + "; ".join(f"{c['name']}={c.get('pitch_mode')}" for c in sorted(done, key=lambda c: c['name'])))
                online = sum(1 for c in done if c.get("pitch_mode") == "online")
                onsite = sum(1 for c in done if c.get("pitch_mode") == "onsite")
                rows.append((item["title"], len(cards), submitted, online, onsite))

    total = sum(r[1] for r in rows)
    for title, seated, submitted, online, onsite in rows:
        print(
            f"{seated:>3} participants, {submitted:>3} submitted "
            f"({online} online, {onsite} onsite)  |  {title[:60]}"
        )
    print(f"\ndistinct people across all tracks: {len(people)}")
    print(f"\nsubmitted by pitch mode: {modes}")
    print(f"\ntracks: {len(rows)}  participants: {total}  average per track: {total / len(rows):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
