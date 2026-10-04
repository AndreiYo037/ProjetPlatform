"""Backfill apply_access_code on the 15 Startup Shuffle challenges.

They were created and published via create_startup_shuffle_challenges.py at
2026-10-04 19:35 UTC. The "Gate on-site apply behind start time and a room
access code" commit landed ~10 minutes later and only sets the code at
create or publish time, so these 15 rows were never touched: NULL code means
apply() 403s for every applicant, always (see apps/api/projet/api/public.py).

Fix: re-POST /programmes/{id}/publish on each. publish_programme() backfills
a fresh apply_access_code when the programme is onsite and the field is
still empty, and republishing an already-open programme is a no-op
otherwise (publish() just sets status=OPEN, which it already is).

Prints each company's resulting code, since that's what they hand out in
the room — nothing else to act on besides reading those back to the user.
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")


class Target(TypedDict):
    email: str
    slug: str
    title: str


TARGETS: list[Target] = [
    {
        "email": "maybelsan2801@gmail.com",
        "slug": "product-engineer-intern",
        "title": "Product Engineer Intern",
    },
    {
        "email": "maybelsan2801@gmail.com",
        "slug": "medical-clinical-intern",
        "title": "Medical / Clinical Intern",
    },
    {"email": "maybelsan2801@gmail.com", "slug": "gtm-intern", "title": "GTM Intern"},
    {"email": "kayhngquek@gmail.com", "slug": "gtm-intern", "title": "GTM Intern"},
    {"email": "kayhngquek@gmail.com", "slug": "video-intern", "title": "Video Intern"},
    {
        "email": "e1356491@u.nus.edu",
        "slug": "greater-china-market-entry-commercial-strategy-intern",
        "title": "Greater China Market Entry & Commercial Strategy Intern",
    },
    {
        "email": "e1356491@u.nus.edu",
        "slug": "brand-ecosystem-customer-growth-intern",
        "title": "Brand Ecosystem & Customer Growth Intern",
    },
    {
        "email": "e1356491@u.nus.edu",
        "slug": "growth-experimentation-customer-analytics-intern",
        "title": "Growth Experimentation & Customer Analytics Intern",
    },
    {
        "email": "rija.hilmi@gmail.com",
        "slug": "product-development-intern",
        "title": "Product Development Intern",
    },
    {"email": "sindhu@snowball.day", "slug": "growth", "title": "Growth"},
    {
        "email": "hello@thirdspacesmarketing.com",
        "slug": "growth-intern-full-time",
        "title": "Growth Intern (Full-Time)",
    },
    {
        "email": "hello@thirdspacesmarketing.com",
        "slug": "sales-and-accounts-associate-part-time",
        "title": "Sales and Accounts Associate (Part-Time)",
    },
    {
        "email": "eugenewang1227@gmail.com",
        "slug": "mobile-software-engineering-intern",
        "title": "Mobile Software Engineering Intern",
    },
    {
        "email": "eugenewang1227@gmail.com",
        "slug": "product-design-ui-ux-intern",
        "title": "Product Design (UI/UX) Intern",
    },
    {
        "email": "eugenewang1227@gmail.com",
        "slug": "business-partnerships-intern",
        "title": "Business & Partnerships Intern",
    },
]


def _login(client: httpx.Client, email: str) -> bool:
    resp = client.post(
        "/auth/login",
        json={"actor_type": "company_user", "email": email, "password": PASSWORD},
    )
    if resp.status_code != 200:
        print(f"  !! login failed for {email}: {resp.status_code} {resp.text[:200]}")
        return False
    return True


def _backfill_one(client: httpx.Client, slug: str, title: str) -> str | None:
    listing = client.get("/programmes")
    if listing.status_code != 200:
        print(f"  !! could not list programmes: {listing.status_code} {listing.text[:200]}")
        return None
    programme_id = None
    for row in listing.json():
        if row.get("slug") == slug:
            programme_id = row["id"]
            break
    if programme_id is None:
        print(f"  !! {title} ({slug}): not found")
        return None

    pub = client.post(f"/programmes/{programme_id}/publish")
    if pub.status_code != 200:
        print(f"  !! publish failed for {title}: {pub.status_code} {pub.text[:300]}")
        return None

    code = pub.json().get("apply_access_code")
    print(f"  {title}: code = {code}")
    return code


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set — refusing to run with no password.", file=sys.stderr)
        return 2

    by_email: dict[str, list[Target]] = {}
    for item in TARGETS:
        by_email.setdefault(item["email"], []).append(item)

    failed = 0
    for email, items in by_email.items():
        print(f"\n{email}")
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            if not _login(client, email):
                failed += len(items)
                continue
            for item in items:
                if _backfill_one(client, item["slug"], item["title"]) is None:
                    failed += 1

    print(f"\n{len(TARGETS) - failed}/{len(TARGETS)} access codes confirmed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
