"""Email participants that their signed testimonial was reissued.

Only the named participants, only letters that are signed, and only once per
signing (the API dedupes). Dry run unless APPLY=1.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
APPLY = os.environ.get("APPLY") == "1"
MATCH = (os.environ.get("COMPANY_MATCH") or "beez").lower()
NAMES = [n.strip().lower() for n in (os.environ.get("NAMES") or "").split(";") if n.strip()]


def main() -> int:
    if not PASSWORD or not NAMES:
        print("COMPANY_PASSWORD and NAMES are required.", file=sys.stderr)
        return 2
    for email in sorted({i["email"] for i in CHALLENGES if MATCH in i["email"].lower()}):
        with httpx.Client(base_url=API_BASE, timeout=60) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                return 1
            for programme in client.get("/programmes").json():
                pid = programme["id"]
                for card in client.get(f"/programmes/{pid}/submissions").json():
                    if not any(n in card["name"].lower() for n in NAMES):
                        continue
                    base = f"/programmes/{pid}/participants/{card['participant_id']}/testimonial"
                    t = client.get(base).json()
                    if not t or not t.get("signed"):
                        print(f"skip {card['name']}: no signed letter")
                        continue
                    if not APPLY:
                        print(f"would email {card['name']}")
                        continue
                    sent = client.post(f"{base}/notify")
                    print(f"{card['name']}: {sent.status_code} {sent.text}")
    print("\nDry run only. No email sent." if not APPLY else "\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
