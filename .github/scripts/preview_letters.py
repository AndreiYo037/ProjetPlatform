"""Read-only: dump what each saved testimonial letter is made of.

Prints, per testimonial, the stored letter parts as JSON, and the company logo
shrunk to a small PNG as base64, so the letter can be re-rendered for preview.
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys

import httpx
from PIL import Image

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
            logo_done = False
            for programme in client.get("/programmes").json():
                pid = programme["id"]
                for card in client.get(f"/programmes/{pid}/submissions").json():
                    base = f"/programmes/{pid}/participants/{card['participant_id']}/testimonial"
                    t = client.get(base).json()
                    if not t:
                        continue
                    ctx = client.get(f"{base}/context").json()
                    if not logo_done and ctx.get("company_logo_url"):
                        raw = client.get(ctx["company_logo_url"]).content
                        img = Image.open(io.BytesIO(raw)).convert("RGBA")
                        img.thumbnail((360, 120))
                        out = io.BytesIO()
                        img.save(out, "PNG", optimize=True)
                        print("LOGO " + base64.b64encode(out.getvalue()).decode())
                        logo_done = True
                    keep = (
                        "recipients", "body", "signoff_name", "signoff_title",
                        "signoff_company", "company_details", "signed", "signed_at",
                        "signature_typed", "own_file",
                    )
                    row = {k: t.get(k) for k in keep}
                    row["participant"] = card["name"]
                    row["programme_title"] = ctx.get("programme_title")
                    print("LETTER " + json.dumps(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
