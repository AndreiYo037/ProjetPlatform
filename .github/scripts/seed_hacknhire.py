"""Create the Hack n Hire company accounts over the public API: signup,
profile (name, website) and logo, per company.

The account password is COMPANY_PASSWORD, passed in as a workflow input at
run time — never committed. Idempotent: an email that already has an account
logs in instead, and the profile and logo are re-applied (a logo file here is
a deliberate "use this one", so it always overwrites).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TypedDict

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("COMPANY_PASSWORD")
LOGOS_DIR = Path(__file__).parent / "logos_hacknhire"

CONTENT_TYPE_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class CompanySeed(TypedDict):
    email: str
    name: str
    website_url: str
    logo: str


COMPANIES: list[CompanySeed] = [
    {
        "email": "shutong.wang@bluenexus.tech",
        "name": "BlueNexus",
        "website_url": "https://bluenexus.tech",
        "logo": "bluenexus.png",
    },
    {
        "email": "brice@bizsu.co",
        "name": "Bizsu",
        "website_url": "https://bizsu.co",
        "logo": "bizsu.png",
    },
    {
        "email": "nico@beez-fm.com",
        "name": "beez-fm",
        "website_url": "https://beez-fm.com",
        "logo": "beez-fm.png",
    },
    {
        "email": "matthew.saw@systemearth.com",
        "name": "SystemEarth",
        "website_url": "https://systemearth.com",
        "logo": "systemearth.webp",
    },
]


def _sign_in_or_up(client: httpx.Client, email: str) -> str | None:
    creds = {"actor_type": "company_user", "email": email, "password": PASSWORD}
    resp = client.post("/auth/signup", json=creds)
    if resp.status_code == 201:
        print(f"  account created ({email})")
        return resp.json()["company_id"]
    if resp.status_code == 409:
        resp = client.post("/auth/login", json=creds)
        if resp.status_code == 200:
            print(f"  account already existed, signed in ({email})")
            return resp.json()["company_id"]
        print(f"  !! {email} already has an account under a different password")
        return None
    print(f"  !! signup failed for {email}: {resp.status_code} {resp.text[:200]}")
    return None


def _seed_one(client: httpx.Client, entry: CompanySeed) -> bool:
    company_id = _sign_in_or_up(client, entry["email"])
    if company_id is None:
        return False

    resp = client.patch(
        f"/companies/{company_id}",
        json={"name": entry["name"], "website_url": entry["website_url"]},
    )
    if resp.status_code != 200:
        print(f"  !! profile update failed: {resp.status_code} {resp.text[:200]}")
        return False
    print(f"  profile set: {entry['name']} / {entry['website_url']}")

    path = LOGOS_DIR / entry["logo"]
    content_type = CONTENT_TYPE_BY_SUFFIX[path.suffix.lower()]
    resp = client.post(
        f"/companies/{company_id}/logo",
        files={"file": (path.name, path.read_bytes(), content_type)},
    )
    if resp.status_code != 201:
        print(f"  !! logo upload failed: {resp.status_code} {resp.text[:200]}")
        return False
    print(f"  logo uploaded: {path.name}")
    return True


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set — refusing to run.", file=sys.stderr)
        return 2

    failed = 0
    for entry in COMPANIES:
        print(f"\n{entry['name']} ({entry['email']})")
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            if not _seed_one(client, entry):
                failed += 1

    print(f"\n{len(COMPANIES) - failed}/{len(COMPANIES)} companies set up.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
