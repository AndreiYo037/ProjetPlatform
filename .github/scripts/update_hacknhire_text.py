"""Push the brief and deliverables in create_hacknhire_challenges.py to one
live challenge, by slug. Touches only problem_statement and deliverable_spec.

COMPANY_PASSWORD and SLUG are workflow inputs.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
SLUG = os.environ.get("SLUG")


def main() -> int:
    if not PASSWORD or not SLUG:
        print("COMPANY_PASSWORD and SLUG must both be set.", file=sys.stderr)
        return 2
    item = next((c for c in CHALLENGES if c["slug"] == SLUG), None)
    if item is None:
        print(f"No challenge with slug {SLUG!r} in create_hacknhire_challenges.py.")
        return 1

    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": item["email"], "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code} {login.text[:200]}")
            return 1
        rows = client.get("/programmes").json()
        programme_id = next((r["id"] for r in rows if r.get("slug") == SLUG), None)
        if programme_id is None:
            print(f"!! {SLUG} not found on {item['email']}")
            return 1
        resp = client.patch(
            f"/programmes/{programme_id}",
            json={
                "problem_statement": item["problem_statement"],
                "deliverable_spec": item["deliverable_spec"],
            },
        )
        if resp.status_code != 200:
            print(f"!! update failed: {resp.status_code} {resp.text[:300]}")
            return 1
    print(f"updated brief and deliverables: {item['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
