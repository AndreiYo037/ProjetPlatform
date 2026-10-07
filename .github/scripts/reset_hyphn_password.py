"""One-off: reset Hyphn's company account password to a chosen value.

Hyphn's founder couldn't sign in with the password they had (the real
SEED_PASSWORD secret value is masked and was never shared with them). This
logs in with the known-working SEED_PASSWORD secret, then uses the
self-service PATCH /auth/me/password endpoint to set a new password for
that one account — read from NEW_PASSWORD at runtime, never hardcoded.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
NEW_PASSWORD = os.environ.get("NEW_PASSWORD")
EMAIL = "verrell88.kc@gmail.com"


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2
    if not NEW_PASSWORD:
        print("NEW_PASSWORD is not set.", file=sys.stderr)
        return 2

    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        login = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
        )
        if login.status_code != 200:
            print(f"!! login failed for {EMAIL}: {login.status_code} {login.text[:200]}")
            return 1

        resp = client.patch("/auth/me/password", json={"password": NEW_PASSWORD})
        if resp.status_code != 200:
            print(f"!! password change failed: {resp.status_code} {resp.text[:300]}")
            return 1
        print(f"password reset for {EMAIL}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
