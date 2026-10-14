"""Read-only: has the Render deploy picked up the submission memo / pitch-mode API?"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
WANTED = ("/me/submission/memo", "/me/submission/pitch-mode")


def main() -> int:
    paths = httpx.get(f"{API_BASE}/openapi.json", timeout=60).json()["paths"]
    missing = [p for p in WANTED if p not in paths]
    for path in WANTED:
        print(f"{path}: {'live' if path in paths else 'NOT live yet'}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
