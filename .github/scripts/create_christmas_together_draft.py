"""Create the Beans&Beats x Christmas Together 2026 queue-system challenge.

Same path as every other challenge: the public API, signed in as the existing
Beans&Beats company account (SEED_PASSWORD secret). On-site, no access code,
Software Engineering, no seat cap. Publishes only when PUBLISH=1.

The challenge was first created online. Delivery mode can't be edited, so an
online draft under this slug is deleted (drafts only) and recreated on-site.
Before touching anything it checks the live API supports require_apply_code,
so an un-deployed API can't leave the challenge deleted.

Idempotent on slug: a re-run on the on-site version updates its brief and
deliverables instead of creating a second one.
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
- Pitch day: 8 Nov 2026
- After the programme: the winner hardens the build 9 to 13 Nov, barista dry run the week of 16 Nov, and the build runs live 26 to 29 Nov with the team on call.

Eligibility: open to anyone, solo or in teams of any size. The winning team must be available for the dry run week of 16 Nov and on call 26 to 29 Nov."""

DELIVERABLE_SPEC = """\
All four are required:
1. Live deployed link to all six modules, with test logins for barista and booth-lead views
2. Repo link with a README covering setup, deployment and resetting between event days
3. 3-minute demo video: one order from order screen to guest alert to ready board, including a wifi drop and recovery
4. 1-page technical summary PDF: stack and architecture, how it works offline and syncs, what personal data is stored and how it meets PDPA, known limitations

Put the live link, demo video link and technical summary PDF link at the top of your repo README, and submit the repo link as your artifact."""


def _login(client: httpx.Client) -> str | None:
    login = client.post(
        "/auth/login",
        json={"actor_type": "company_user", "email": EMAIL, "password": PASSWORD},
    )
    if login.status_code != 200:
        print(f"!! login failed: {login.status_code} {login.text[:200]}")
        return None
    return login.json()["company_id"]


def main() -> int:
    if not PASSWORD:
        print("SEED_PASSWORD is not set.", file=sys.stderr)
        return 2
    publish = os.environ.get("PUBLISH") == "1"

    with httpx.Client(base_url=API_BASE, timeout=60) as client:
        if "require_apply_code" not in client.get("/openapi.json").text:
            print(
                "!! live API doesn't support require_apply_code yet (not deployed); nothing changed"
            )
            return 3
        company_id = _login(client)
        if company_id is None:
            return 1

        existing = next(
            (r for r in client.get("/programmes").json() if r.get("slug") == SLUG), None
        )
        if existing is not None and existing["delivery_mode"] != "in_person":
            if existing["status"] != "draft":
                print(
                    f"!! online version is {existing['status']}, not a draft; refusing to delete"
                )
                return 1
            deleted = client.delete(f"/programmes/{existing['id']}")
            if deleted.status_code != 204:
                print(f"!! delete failed: {deleted.status_code} {deleted.text[:300]}")
                return 1
            print(f"deleted online draft {existing['id']}")
            existing = None

        if existing is None:
            roles = client.get("/roles/clusters").json()
            role_id = next(
                (r["id"] for c in roles for r in c["roles"] if r["name"] == ROLE_NAME),
                None,
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
                    "delivery_mode": "in_person",
                    "require_apply_code": False,
                    "capacity": None,
                    "applications_open_at": "2026-10-15T00:00:00+08:00",
                    # On-site rules: applications must close after the start.
                    "applications_close_at": "2026-10-25T23:59:00+08:00",
                    "start_at": "2026-10-25T00:00:00+08:00",
                    "submit_deadline_at": "2026-11-08T23:59:00+08:00",
                    "problem_statement": PROBLEM_STATEMENT,
                    "deliverable_spec": DELIVERABLE_SPEC,
                },
            )
            if resp.status_code != 201:
                print(f"!! create failed: {resp.status_code} {resp.text[:400]}")
                return 1
            programme = resp.json()
            print(f"created on-site draft: id={programme['id']}")
        else:
            upd = client.patch(
                f"/programmes/{existing['id']}",
                json={
                    "problem_statement": PROBLEM_STATEMENT,
                    "deliverable_spec": DELIVERABLE_SPEC,
                    "require_apply_code": False,
                },
            )
            if upd.status_code != 200:
                print(f"!! update failed: {upd.status_code} {upd.text[:300]}")
                return 1
            programme = upd.json()
            print(f"already on-site, text updated: id={programme['id']}")

        if programme.get("apply_access_code"):
            print("!! an access code is still set; not publishing")
            return 1
        print(f"company page path: /company/challenges/{programme['id']}")

        if publish and programme["status"] == "draft":
            pub = client.post(f"/programmes/{programme['id']}/publish")
            if pub.status_code != 200:
                print(f"!! publish failed: {pub.status_code} {pub.text[:300]}")
                return 1
            programme = pub.json()
            if programme.get("apply_access_code"):
                print("!! publish set an access code")
                return 1
            print(f"published: status={programme['status']}")
        print(f"status={programme['status']} access_code=none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
