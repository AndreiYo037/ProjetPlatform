"""Read-only: does a company's testimonial letter have a logo to print?

Prints the logo the letter context reports for each testimonial and whether
those bytes actually load.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
MATCH = (os.environ.get("COMPANY_MATCH") or "beez").lower()


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
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
                    base = f"/programmes/{pid}/participants/{card['participant_id']}/testimonial"
                    t = client.get(base).json()
                    if not t:
                        continue
                    ctx = client.get(f"{base}/context").json()
                    logo = ctx.get("company_logo_url")
                    size = "n/a"
                    if logo:
                        got = client.get(logo)
                        size = f"{got.status_code}, {len(got.content)} bytes"
                    print(
                        f"{card['name']}: signed={t.get('signed')} logo_url={logo} "
                        f"fetch={size} pdf={'yes' if t.get('pdf_url') else 'no'}"
                    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
