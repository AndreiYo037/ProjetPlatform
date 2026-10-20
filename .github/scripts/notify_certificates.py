"""Email the people on each issued certificate that it is ready.

Dry run unless APPLY=1: a dry run lists who would be emailed and sends nothing.
Only the participant who submitted gets the email (the team contact). The API sends one email per person per issued certificate, so running it twice
does not double-send.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
APPLY = os.environ.get("APPLY") == "1"


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    total = 0
    for email in sorted({i["email"] for i in CHALLENGES}):
        with httpx.Client(base_url=API_BASE, timeout=120) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                return 1
            for programme in client.get("/programmes").json():
                if programme.get("status") != "complete":
                    continue
                reply = client.post(
                    f"/programmes/{programme['id']}/certificates/notify",
                    json={"dry_run": not APPLY, "submitter_only": True},
                )
                print("=" * 70)
                print(programme["title"][:70])
                if reply.status_code != 200:
                    print(f"  failed {reply.status_code}: {reply.text[:200]}")
                    continue
                body = reply.json()
                total += len(body["recipients"])
                print(f"  {'queued' if APPLY else 'would email'} {len(body['recipients'])}: "
                      f"{', '.join(body['recipients'])}")
    print(f"\n{total} email(s) {'queued' if APPLY else 'would be sent'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
