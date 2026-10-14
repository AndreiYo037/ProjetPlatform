"""Read-only: what is production actually serving as a company's logo?

Logs in as the company, reads the stored logo reference, fetches the logo
bytes straight from the API (bypassing any browser or CDN in front), and
prints size, hash and cache headers so it can be compared to the file that
was uploaded.
"""

from __future__ import annotations

import hashlib
import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = os.environ.get("CHECK_EMAIL", "hello@thirdspacesmarketing.com")


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2
    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed: {login.status_code}")
            return 1
        company_id = login.json()["company_id"]
        home = client.get(f"/companies/{company_id}/home").json()["company"]
        print(f"company: {home['name']}  logo_url field: {home.get('logo_url')}")
        for label, url in (
            ("plain", f"/companies/{company_id}/logo"),
            ("cache-busted", f"/companies/{company_id}/logo?nocache=1"),
        ):
            r = client.get(url)
            digest = hashlib.sha256(r.content).hexdigest()[:16]
            print(
                f"{label}: status={r.status_code} bytes={len(r.content)} "
                f"sha256={digest} type={r.headers.get('content-type')} "
                f"cache-control={r.headers.get('cache-control')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
