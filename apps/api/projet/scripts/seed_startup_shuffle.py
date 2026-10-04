"""One-off: create the 8 Startup Shuffle company accounts from the founder CSV.

Why a script instead of calling the API: the environment that authored this
ran with no outbound network access at all (not even to this platform's own
domain), so it could not call /auth/signup itself. This calls the exact same
service-layer functions the API route does (register_account, the company
profile update, the logo upload path), so the result is identical to what
clicking through the real signup form would produce. Run it from somewhere
that has internet access and the production PROJET_DATABASE_URL — a Render
shell for the API service is the normal place for that:

    python -m projet.scripts.seed_startup_shuffle

Idempotent: re-running skips any email that already has a password set, and
only fills in a logo if the company doesn't have one yet. Safe to re-run
after a partial failure (e.g. a logo fetch timing out).

B71 SCAPS (row 9 of the source CSV) is deliberately not in COMPANIES: the
source row has no website, no LinkedIn and no description to work from.
"""

from __future__ import annotations

import io
import re
import sys
from typing import TypedDict

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from projet.db import get_sessionmaker
from projet.models.company import Company, CompanyUser
from projet.models.enums import ActorType
from projet.services.auth import SignupError, register_account, resolve_actor_of_type
from projet.services.branding import LOGO_TYPES, MAX_LOGO_BYTES, new_logo_key
from projet.storage import get_storage

PASSWORD = "startupshuffle1234"


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


def _ensure_account(session: Session, email: str, password: str) -> Company:
    """Create the company_user account if it doesn't exist. Returns its Company row."""
    existing_id = resolve_actor_of_type(session, email, ActorType.COMPANY_USER)
    if existing_id is None:
        try:
            register_account(
                session, actor_type=ActorType.COMPANY_USER, email=email, password=password
            )
            session.flush()
        except SignupError as exc:
            raise RuntimeError(f"signup failed for {email}: {exc}") from exc
        existing_id = resolve_actor_of_type(session, email, ActorType.COMPANY_USER)
        assert existing_id is not None
        print(f"  account created ({email})")
    else:
        print(f"  account already exists ({email}) — left password as-is")

    user = session.get(CompanyUser, existing_id)
    assert user is not None
    company = session.get(Company, user.company_id)
    assert company is not None
    return company


def _apply_profile(company: Company, name: str, website_url: str) -> None:
    company.name = name
    company.website_url = website_url


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
    """Clearbit's public logo API — usually the cleanest, un-cropped mark."""
    found = _fetch_bytes(client, f"https://logo.clearbit.com/{domain}?size=512&format=png")
    if found is None:
        return None
    content, content_type = found
    if content_type != "image/png" or len(content) < 200:
        return None
    return content


def _logo_via_og_image(client: httpx.Client, page_url: str) -> bytes | None:
    """Fall back to whatever the page itself declares as its share image."""
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


def _normalise_for_upload(raw: bytes) -> tuple[bytes, str] | None:
    """Validate it actually opens, re-encode to an accepted raster type, and
    scale down (never crop) if it's over the 2MB upload limit."""
    try:
        opened = Image.open(io.BytesIO(raw))
        opened.load()
    except Exception:
        return None

    image: Image.Image = opened.convert("RGBA" if opened.mode in ("P", "RGBA", "LA") else "RGB")
    fmt, content_type = "PNG", "image/png"

    buf = io.BytesIO()
    image.save(buf, format=fmt)
    content = buf.getvalue()

    scale = 0.85
    while len(content) > MAX_LOGO_BYTES and scale > 0.1:
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format=fmt)
        content = buf.getvalue()
        image = resized
        scale -= 0.15

    if len(content) > MAX_LOGO_BYTES:
        return None
    assert content_type in LOGO_TYPES
    return content, content_type


def _apply_logo(company: Company, client: httpx.Client, domain: str | None, page: str) -> bool:
    if company.logo_url:
        print(f"  logo already set for {company.name} — leaving it")
        return True

    raw = None
    if domain:
        raw = _logo_via_clearbit(client, domain)
    if raw is None:
        raw = _logo_via_og_image(client, page)
    if raw is None:
        print(f"  !! no logo found for {company.name} — leave blank, upload manually")
        return False

    normalised = _normalise_for_upload(raw)
    if normalised is None:
        print(f"  !! fetched a logo for {company.name} but couldn't make it fit — upload manually")
        return False

    content, content_type = normalised
    key = new_logo_key(company.id, content_type)
    get_storage().put(key, content, content_type)
    company.logo_url = key
    print(f"  logo set for {company.name} ({len(content) // 1024}KB)")
    return True


def main() -> int:
    session_factory = get_sessionmaker()
    created, logo_ok, logo_missing = 0, 0, 0

    with session_factory() as session, httpx.Client(headers={"User-Agent": _UA}) as client:
        for entry in COMPANIES:
            print(f"\n{entry['name']} ({entry['email']})")
            company = _ensure_account(session, entry["email"], PASSWORD)
            _apply_profile(company, entry["name"], entry["website_url"])
            ok = _apply_logo(company, client, entry["logo_domain"], entry["logo_page"])
            logo_ok += int(ok)
            logo_missing += int(not ok)
            created += 1
            session.commit()

    print(
        f"\n{created} companies processed — {logo_ok} logos set, "
        f"{logo_missing} need a manual upload."
    )
    print(f"Password for all: {PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
