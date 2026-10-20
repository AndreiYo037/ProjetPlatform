"""Read-only: has each certificate email actually gone out?

Prints every certificate email in the send queue for each closed challenge,
with its status (pending / done / failed), attempts and any error.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
ONLY = (os.environ.get("ONLY") or "").strip().lower()


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    totals: dict[str, int] = {}
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
                reply = client.get(f"/programmes/{programme['id']}/certificates/emails")
                print("=" * 70)
                print(programme["title"][:70])
                if reply.status_code != 200:
                    print(f"  failed {reply.status_code}: {reply.text[:200]}")
                    continue
                for row in reply.json():
                    if ONLY and ONLY not in row["to_name"].lower():
                        continue
                    totals[row["status"]] = totals.get(row["status"], 0) + 1
                    error = f"  error: {row['last_error'][:120]}" if row["last_error"] else ""
                    kind = row.get("kind", "certificate")
                    if row.get("mentions_testimonial"):
                        kind += "+testimonial"
                    print(
                        f"  {kind:<20} {row['subject'][:40]:<40} {row['status']:<8} tries {row['attempts']}  "
                        f"sent {row['sent_at'] or '-'}  {row['to_name']}{error}"
                    )
    print(f"\nTotals: {totals}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
