"""Read-only: does this password sign in to the Beans&Beats company account?"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("CANDIDATE_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"


def main() -> int:
    if not PASSWORD:
        print("CANDIDATE_PASSWORD is not set.", file=sys.stderr)
        return 2
    with httpx.Client(base_url=API_BASE, timeout=60) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
    print(f"LOGIN | {login.status_code} | {'works' if login.status_code == 200 else 'does not work'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
