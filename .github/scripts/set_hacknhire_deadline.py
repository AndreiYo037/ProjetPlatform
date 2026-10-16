"""Set the submission deadline on every Hack n Hire track.

Logs in as each of the four company accounts and PATCHes submit_deadline_at on
that company's Hack n Hire challenges. Nothing else is touched.
COMPANY_PASSWORD is a workflow input.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES, END_AT

PASSWORD = os.environ.get("COMPANY_PASSWORD")


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    by_email: dict[str, list[dict]] = {}
    for item in CHALLENGES:
        by_email.setdefault(item["email"], []).append(item)

    failed = 0
    for email, items in by_email.items():
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                failed += len(items)
                continue
            programmes = {r["slug"]: r for r in client.get("/programmes").json()}
            for item in items:
                row = programmes.get(item["slug"])
                if row is None:
                    print(f"!! {item['slug']} not found")
                    failed += 1
                    continue
                resp = client.patch(
                    f"/programmes/{row['id']}", json={"submit_deadline_at": END_AT}
                )
                if resp.status_code != 200:
                    print(f"!! {item['slug']}: {resp.status_code} {resp.text[:200]}")
                    failed += 1
                    continue
                print(
                    f"{row['submit_deadline_at']} -> {resp.json()['submit_deadline_at']}"
                    f"  |  {item['title'][:60]}"
                )
    print(f"\n{len(CHALLENGES) - failed}/{len(CHALLENGES)} updated")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
