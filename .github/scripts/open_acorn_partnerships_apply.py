"""Open applications early for Acorn Labs — Business & Partnerships Intern.

On-site challenges normally only accept applications from start_at. Setting
applications_open_at to now opts this one challenge into an early window;
submissions still wait for start.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")

EMAIL = "eugenewang1227@gmail.com"
SLUG = "business-partnerships-intern"
TITLE = "Business & Partnerships Intern"


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is required", file=sys.stderr)
        return 1

    with httpx.Client(base_url=API_BASE, timeout=60.0) as client:
        login = client.post(
            "/auth/login",
            json={
                "actor_type": "company_user",
                "email": EMAIL,
                "password": PASSWORD,
            },
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code} {login.text[:200]}")
            return 1

        listing = client.get("/programmes")
        if listing.status_code != 200:
            print(f"!! list failed: {listing.status_code} {listing.text[:200]}")
            return 1

        programme_id = None
        for row in listing.json():
            if row.get("slug") == SLUG:
                programme_id = row["id"]
                break
        if programme_id is None:
            print(f"!! {TITLE} ({SLUG}): not found")
            return 1

        opened = datetime.now(UTC).replace(microsecond=0).isoformat()
        resp = client.patch(
            f"/programmes/{programme_id}",
            json={"applications_open_at": opened},
        )
        if resp.status_code != 200:
            print(f"!! update failed: {resp.status_code} {resp.text[:300]}")
            return 1

        # Confirm public state is open (company slug was company-N at seed time).
        public = client.get(f"/public/x/company-9/{SLUG}")
        if public.status_code != 200:
            # Fall back to directory lookup if the company slug differs.
            directory = client.get("/public/challenges", params={"limit": 100})
            state = "?"
            if directory.status_code == 200:
                for row in directory.json():
                    if row.get("programme_slug") == SLUG:
                        state = row.get("state", "?")
                        break
        else:
            state = public.json().get("state", "?")
        print(f"ok: {TITLE} applications_open_at={opened} public_state={state}")
        return 0 if state == "open" else 1


if __name__ == "__main__":
    raise SystemExit(main())
