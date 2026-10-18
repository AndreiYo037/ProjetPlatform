"""Read-only: which Hack n Hire participants already have a testimonial.

The GET only returns the testimonial written by the signed-in user, so this
sees what each company account itself wrote. Makes no writes.
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

    found = 0
    for email, items in by_email.items():
        with httpx.Client(base_url=API_BASE, timeout=60) as client:
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
                    continue
                cards = client.get(f"/programmes/{row['id']}/submissions").json()
                for card in cards:
                    resp = client.get(
                        f"/programmes/{row['id']}/participants/{card['participant_id']}/testimonial"
                    )
                    if resp.status_code != 200 or not resp.json():
                        continue
                    t = resp.json()
                    found += 1
                    state = "published" if t.get("published_at") else "draft"
                    kind = "own file" if t.get("own_file") else "generated"
                    print(
                        f"{state:>9} | {kind:>9} | {len(t.get('body') or ''):>4} chars | "
                        f"{card['name'][:28]:<28} | {item['title'][:34]}"
                    )
    print(f"\n{found} testimonial(s) found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
