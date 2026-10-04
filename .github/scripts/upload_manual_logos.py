"""Upload a manually-sourced logo for a Startup Shuffle company.

Companion to seed_startup_shuffle.py: that script flagged PĒRL, Maleo Systems,
Snowball and Acorn Labs as having no logo it could find automatically. Drop a
PNG/JPEG/WebP file in .github/scripts/logos/ named after the key below, and
this uploads it to that company's account over the public API — same
mechanism as the signup script (no database credentials, runs from GitHub
Actions for the internet access this platform's own domain needs).

Always overwrites: unlike the seed script, a file placed here is a deliberate
"use this one" instruction, not a best-effort guess.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
LOGOS_DIR = Path(__file__).parent / "logos"

# File stem -> the company account's email (must match seed_startup_shuffle.py).
ACCOUNT_BY_KEY = {
    "perl": "maybelsan2801@gmail.com",
    "maleo-systems": "rija.hilmi@gmail.com",
    "snowball": "sindhu@snowball.day",
    "acorn-labs": "eugenewang1227@gmail.com",
}

CONTENT_TYPE_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _upload_one(client: httpx.Client, email: str, path: Path) -> bool:
    content_type = CONTENT_TYPE_BY_SUFFIX.get(path.suffix.lower())
    if content_type is None:
        print(f"  !! {path.name}: unsupported file type, must be PNG/JPEG/WebP")
        return False

    resp = client.post(
        "/auth/login",
        json={"actor_type": "company_user", "email": email, "password": PASSWORD},
    )
    if resp.status_code != 200:
        print(f"  !! login failed for {email}: {resp.status_code} {resp.text[:200]}")
        return False
    company_id = resp.json()["company_id"]

    resp = client.post(
        f"/companies/{company_id}/logo",
        files={"file": (path.name, path.read_bytes(), content_type)},
    )
    if resp.status_code != 201:
        print(f"  !! logo upload failed for {email}: {resp.status_code} {resp.text[:200]}")
        return False

    print(f"  uploaded {path.name} for {email}")
    return True


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set — refusing to run with no password.", file=sys.stderr)
        return 2

    if not LOGOS_DIR.is_dir():
        print(f"No logos directory at {LOGOS_DIR}")
        return 0

    files = sorted(p for p in LOGOS_DIR.iterdir() if p.is_file() and p.name != ".gitkeep")
    if not files:
        print("No logo files to upload.")
        return 0

    failed = 0
    for path in files:
        key = path.stem.lower()
        email = ACCOUNT_BY_KEY.get(key)
        print(f"\n{path.name}")
        if email is None:
            print(f"  !! no account mapped for key '{key}' — add it to ACCOUNT_BY_KEY")
            failed += 1
            continue
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            if not _upload_one(client, email, path):
                failed += 1

    print(f"\n{len(files) - failed}/{len(files)} logo(s) uploaded.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
