"""Set apply_access_code on the 15 Startup Shuffle challenges to SEED_PASSWORD.

Supersedes the per-challenge random codes from backfill_apply_access_codes.py:
one shared code (the same SEED_PASSWORD used for the 8 company account
logins) is easier to hand out in the room than 15 different ones.

PATCH /programmes/{id} accepts apply_access_code directly; the server
normalises it (strips whitespace, uppercases) and stores that, so this sends
the raw password and lets the server do the normalisation.
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


def _set_one(client: httpx.Client, slug: str, title: str) -> bool:
    listing = client.get("/programmes")
    if listing.status_code != 200:
        print(f"  !! could not list programmes: {listing.status_code} {listing.text[:200]}")
        return False
    programme_id = None
    for row in listing.json():
        if row.get("slug") == slug:
            programme_id = row["id"]
            break
    if programme_id is None:
        print(f"  !! {title} ({slug}): not found")
        return False

    resp = client.patch(f"/programmes/{programme_id}", json={"apply_access_code": PASSWORD})
    if resp.status_code != 200:
        print(f"  !! update failed for {title}: {resp.status_code} {resp.text[:300]}")
        return False

    code = resp.json().get("apply_access_code")
    print(f"  {title}: code = {code}")
    return True


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
                if not _set_one(client, item["slug"], item["title"]):
                    failed += 1

    print(f"\n{len(TARGETS) - failed}/{len(TARGETS)} access codes set to SEED_PASSWORD.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
