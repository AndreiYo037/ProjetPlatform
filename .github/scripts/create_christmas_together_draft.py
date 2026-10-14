"""Create the Beans&Beats x Christmas Together 2026 queue-system challenge as
a DRAFT — never published by this script.

Same path as every other challenge: the public API, signed in as the existing
Beans&Beats company account (SEED_PASSWORD secret). Online, Software
Engineering, no seat cap. Kickoff and the pitch schedule are left unset on
purpose: no times were given, and setting a pitch schedule creates a Calendar
event. Both must be set before publishing.

Idempotent on slug: a 409 reports the existing draft instead of creating a
second one.
"""

from __future__ import annotations

import os
import sys

import httpx

API_BASE = os.environ.get("PROJET_API_BASE_URL", "https://projetplatform.onrender.com")
PASSWORD = os.environ.get("SEED_PASSWORD")
EMAIL = "hello@thirdspacesmarketing.com"

TITLE = "Beans&Beats x Christmas Together 2026 Queue Management System"
SLUG = "christmas-together-2026-queue-management-system"
ROLE_NAME = "Software Engineering"

PROBLEM_STATEMENT = """\
Build the order and pickup system for Beans&Beats' charity coffee booth at Christmas Together, Singapore's largest indoor Christmas festival (40,000+ visitors, 26 to 29 Nov 2026, Hall F, Marina Bay Sands). Guests should know the moment their drink is ready, the way Luckin does. The winning build runs live for four days. All profits go to Singapore Red Cross Young Hearts.

What to build (six modules):
1. Order screen: baristas key in drink, milk, hot or iced, and a first name on a tablet. Each order gets a number.
2. Barista queue: orders in sequence, one tap to mark making, one tap to mark ready.
3. Guest status page: guests scan a QR code at the counter to follow their order live, with an alert when it's ready.
4. Ready board: a screen at the booth showing names and numbers waiting to be collected.
5. Menu controls: change items, prices and what's sold out during the day.
6. Daily sales report: cups and totals per day, exported to CSV to match the organiser's POS.

Hard requirements:
- Runs in a browser on tablets and guests' phones, no app to download
- Works offline on patchy hall wifi and syncs later
- First name only; mobile optional, handled under PDPA
- Payments stay on the organiser's POS, outside this build

Timeline (Asia/Singapore):
- Applications: 15 Oct to 24 Oct 2026, 23:59
- Build (Stage 1): 25 Oct to 8 Nov 2026
- Submission deadline: 8 Nov 2026, before pitches start
- Pitch day: 8 Nov 2026 (5 min live demo + 5 min Q&A)
- After the programme: the winner hardens the build 9 to 13 Nov, barista dry run the week of 16 Nov, and the build runs live 26 to 29 Nov with the team on call.

Eligibility: open to anyone, solo or in teams of any size. The winning team must be available for the dry run week of 16 Nov and on call 26 to 29 Nov.

When you apply, tell us:
1. Team members and their background (school or work)
2. A link to something you've shipped that real people used (repo, live link or demo)
3. Which stack you would use, and how you would keep the counter working when the wifi drops (max 150 words)
4. Whether your team can do the dry run week of 16 Nov and be on call 26 to 29 Nov (Yes / No)

Rewards:
- Winning team: their software running live at Singapore's largest indoor Christmas festival, credit on the ready board and in the Beans&Beats recap reel, plus footage for a case study
- Top performers: signed testimonials from Beans&Beats
- Everyone who submits: Projet completion credential and a real project for their portfolio

Contact: Aden Low, Co-founder & Managing Partner, Beans&Beats (general@beansnbeats.com)"""

DELIVERABLE_SPEC = """\
All four are required:
1. Live deployed link to all six modules, with test logins for barista and booth-lead views
2. Repo link with a README covering setup, deployment and resetting between event days
3. 3-minute demo video: one order from order screen to guest alert to ready board, including a wifi drop and recovery
4. 1-page technical summary PDF: stack and architecture, how it works offline and syncs, what personal data is stored and how it meets PDPA, known limitations

Put the live link, demo video link and technical summary PDF link at the top of your repo README, and submit the repo link as your artifact."""


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
            print(f"!! login failed: {login.status_code} {login.text[:200]}")
            return 1
        company_id = login.json()["company_id"]

        roles = client.get("/roles/clusters").json()
        role_id = next(
            (r["id"] for c in roles for r in c["roles"] if r["name"] == ROLE_NAME), None
        )
        if role_id is None:
            print(f"!! role {ROLE_NAME!r} not in taxonomy")
            return 1

        resp = client.post(
            "/programmes",
            json={
                "company_id": company_id,
                "role_ids": [role_id],
                "title": TITLE,
                "slug": SLUG,
                "delivery_mode": "online",
                "capacity": None,
                "applications_open_at": "2026-10-15T00:00:00+08:00",
                "applications_close_at": "2026-10-24T23:59:00+08:00",
                "start_at": "2026-10-25T00:00:00+08:00",
                "submit_deadline_at": "2026-11-08T23:59:00+08:00",
                "problem_statement": PROBLEM_STATEMENT,
                "deliverable_spec": DELIVERABLE_SPEC,
            },
        )
        if resp.status_code == 409:
            existing = next(
                (r for r in client.get("/programmes").json() if r.get("slug") == SLUG), None
            )
            print(f"already exists: id={existing and existing['id']} status={existing and existing['status']}")
            return 0
        if resp.status_code != 201:
            print(f"!! create failed: {resp.status_code} {resp.text[:400]}")
            return 1

        body = resp.json()
        print(f"created draft: id={body['id']} status={body['status']}")
        print(f"company page path: /company/challenges/{body['id']}")
        criteria = client.get(f"/programmes/{body['id']}").json().get("criteria", [])
        for c in criteria:
            print(f"  rubric slot {c.get('slot')}: {c.get('name')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
