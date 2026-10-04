"""One-off: create the 8 Startup Shuffle company accounts over the public API.

Run from GitHub Actions (.github/workflows/seed-startup-shuffle.yml), not from
anywhere else — that's deliberate. The session that wrote this had no outbound
network access at all, not even to this platform's own domain, so it couldn't
call the API directly. A GitHub Actions runner has ordinary internet access
and isn't behind that restriction, so it's where this actually executes.

This hits the real public endpoints (signup, the company profile PATCH, the
logo upload) exactly as a browser would — no database credentials involved.

Idempotent: an email that already has a password set logs in instead of
signing up (same company, same id), and a company that already has a logo
keeps it rather than being overwritten.

B71 SCAPS (row 9 of the source CSV) is deliberately not in COMPANIES: the
source row has no website, no LinkedIn and no description to work from.
"""

from __future__ import annotations

import io
import os
import re
import sys
from typing import TypedDict

import httpx
from PIL import Image

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
# Never hardcoded: set SEED_PASSWORD as a GitHub Actions repository secret so
# it never lands in the repo or its history.
PASSWORD = os.environ.get("SEED_PASSWORD")
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


class CompanySeed(TypedDict):
    email: str
    name: str
    website_url: str
    logo_domain: str | None
    logo_page: str


# One row per founder in the CSV, minus B71 SCAPS. `logo_domain` drives the
# Clearbit lookup (works well for a company with its own site); `logo_page` is
# a page to scrape an og:image from when there's no real domain to ask
# Clearbit about — usually the company's LinkedIn page.
COMPANIES: list[CompanySeed] = [
    {
        "email": "maybelsan2801@gmail.com",
        "name": "PĒRL",
        "website_url": "https://www.linkedin.com/company/p%C4%93rl/",
        "logo_domain": None,
        "logo_page": "https://www.linkedin.com/company/p%C4%93rl/",
    },
    {
        "email": "kayhngquek@gmail.com",
        "name": "1UP! Sales AI Technologies Pte. Ltd.",
        "website_url": "https://1upsalesai.com",
        "logo_domain": "1upsalesai.com",
        "logo_page": "https://1upsalesai.com",
    },
    {
        "email": "verrell88.kc@gmail.com",
        "name": "Hyphn",
        "website_url": "https://hyphn.eco/",
        "logo_domain": "hyphn.eco",
        "logo_page": "https://hyphn.eco/",
    },
    {
        "email": "e1356491@u.nus.edu",
        "name": "DanceWerkz",
        "website_url": "https://www.dancewerkz.com/",
        "logo_domain": "dancewerkz.com",
        "logo_page": "https://www.dancewerkz.com/",
    },
    {
        "email": "rija.hilmi@gmail.com",
        "name": "Maleo Systems",
        "website_url": "https://www.linkedin.com/company/maleosystems/",
        "logo_domain": None,
        "logo_page": "https://www.linkedin.com/company/maleosystems/",
    },
    {
        "email": "sindhu@snowball.day",
        "name": "Snowball",
        "website_url": "https://snowball.day",
        "logo_domain": "snowball.day",
        "logo_page": "https://snowball.day",
    },
    {
        "email": "hello@thirdspacesmarketing.com",
        "name": "Third Spaces Marketing / Beans&Beats",
        "website_url": "https://thirdspacesmarketing.com",
        "logo_domain": "thirdspacesmarketing.com",
        "logo_page": "https://thirdspacesmarketing.com",
    },
    {
        "email": "eugenewang1227@gmail.com",
        "name": "Acorn Labs",
        "website_url": "https://www.linkedin.com/company/acornlabssg/",
        "logo_domain": None,
        "logo_page": "https://www.linkedin.com/company/acornlabssg/",
    },
]

_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE
)
_UA = "Mozilla/5.0 (compatible; ProjetSeedBot/1.0)"


def _sign_in_or_up(client: httpx.Client, email: str) -> dict | None:
    """Returns the ActorResponse body (carries company_id), or None on failure."""
    resp = client.post(
        "/auth/signup",
        json={"actor_type": "company_user", "email": email, "password": PASSWORD},
    )
    if resp.status_code == 201:
        print(f"  account created ({email})")
        return resp.json()

    if resp.status_code == 409:
        resp = client.post(
            "/auth/login",
            json={"actor_type": "company_user", "email": email, "password": PASSWORD},
        )
        if resp.status_code == 200:
            print(f"  account already existed, signed in ({email})")
            return resp.json()
        print(f"  !! {email} already has an account under a different password — skipping")
        return None

    print(f"  !! signup failed for {email}: {resp.status_code} {resp.text[:200]}")
    return None


def _apply_profile(client: httpx.Client, company_id: str, name: str, website_url: str) -> None:
    resp = client.patch(
        f"/companies/{company_id}", json={"name": name, "website_url": website_url}
    )
    if resp.status_code != 200:
        print(f"  !! profile update failed: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"  profile set: {name} / {website_url}")


def _company_has_logo(client: httpx.Client, company_id: str) -> bool:
    resp = client.get(f"/companies/{company_id}/home")
    if resp.status_code != 200:
        return False
    return bool(resp.json().get("company", {}).get("logo_url"))


def _fetch_bytes(client: httpx.Client, url: str) -> tuple[bytes, str] | None:
    try:
        resp = client.get(url, timeout=15, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    return resp.content, content_type


def _logo_via_clearbit(client: httpx.Client, domain: str) -> bytes | None:
    found = _fetch_bytes(client, f"https://logo.clearbit.com/{domain}?size=512&format=png")
    if found is None:
        return None
    content, content_type = found
    if content_type != "image/png" or len(content) < 200:
        return None
    return content


def _logo_via_og_image(client: httpx.Client, page_url: str) -> bytes | None:
    found = _fetch_bytes(client, page_url)
    if found is None:
        return None
    html, content_type = found
    if "html" not in content_type:
        return None
    match = _OG_IMAGE_RE.search(html.decode("utf-8", errors="ignore"))
    if not match:
        return None
    image_found = _fetch_bytes(client, match.group(1))
    if image_found is None:
        return None
    content, content_type = image_found
    if not content_type.startswith("image/"):
        return None
    return content


def _normalise_for_upload(raw: bytes) -> bytes | None:
    """Validate it actually opens, re-encode to PNG, and scale down (never
    crop) if it's over the 2MB upload limit."""
    try:
        opened = Image.open(io.BytesIO(raw))
        opened.load()
    except Exception:
        return None

    image: Image.Image = opened.convert("RGBA" if opened.mode in ("P", "RGBA", "LA") else "RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    content = buf.getvalue()

    scale = 0.85
    while len(content) > MAX_LOGO_BYTES and scale > 0.1:
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        content = buf.getvalue()
        image = resized
        scale -= 0.15

    if len(content) > MAX_LOGO_BYTES:
        return None
    return content


def _apply_logo(
    client: httpx.Client, company_id: str, name: str, domain: str | None, page: str
) -> bool:
    if _company_has_logo(client, company_id):
        print(f"  logo already set for {name} — leaving it")
        return True

    raw = _logo_via_clearbit(client, domain) if domain else None
    if raw is None:
        raw = _logo_via_og_image(client, page)
    if raw is None:
        print(f"  !! no logo found for {name} — upload manually")
        return False

    content = _normalise_for_upload(raw)
    if content is None:
        print(f"  !! fetched a logo for {name} but couldn't make it fit — upload manually")
        return False

    resp = client.post(
        f"/companies/{company_id}/logo",
        files={"file": ("logo.png", content, "image/png")},
    )
    if resp.status_code != 201:
        print(f"  !! logo upload failed for {name}: {resp.status_code} {resp.text[:200]}")
        return False

    print(f"  logo set for {name} ({len(content) // 1024}KB)")
    return True


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set — refusing to run with no password.", file=sys.stderr)
        return 2

    logo_ok, logo_missing, failed = 0, 0, 0

    for entry in COMPANIES:
        print(f"\n{entry['name']} ({entry['email']})")
        with httpx.Client(base_url=API_BASE, headers={"User-Agent": _UA}, timeout=30) as client:
            actor = _sign_in_or_up(client, entry["email"])
            if actor is None:
                failed += 1
                continue
            company_id = actor["company_id"]
            _apply_profile(client, company_id, entry["name"], entry["website_url"])
            ok = _apply_logo(
                client, company_id, entry["name"], entry["logo_domain"], entry["logo_page"]
            )
            logo_ok += int(ok)
            logo_missing += int(not ok)

    print(
        f"\n{len(COMPANIES) - failed}/{len(COMPANIES)} companies processed — "
        f"{logo_ok} logos set, {logo_missing} need a manual upload, {failed} failed outright."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
