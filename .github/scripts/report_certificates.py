"""Read-only: who would get which certificate title, from the scores so far.

One certificate per person. Per challenge, the top half of the scored entries
(rounded up, ties share) get Merit and the rest Completion. A person on several
challenges gets their best title. Teammates share their team's score. Makes no
writes and issues nothing.
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    people: dict[str, dict] = defaultdict(lambda: {"tier": "Completion", "on": []})
    for email in sorted({i["email"] for i in CHALLENGES}):
        with httpx.Client(base_url=API_BASE, timeout=60) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                return 1
            for programme in client.get("/programmes").json():
                cards = client.get(f"/programmes/{programme['id']}/submissions").json()
                scored = [c for c in cards if c["scored"] and c["your_total"] is not None]
                unscored = [
                    c["name"] for c in cards if c["status"] == "submitted" and not c["scored"]
                ]
                # Teammates carry the same score and the same handed-in links.
                entries: dict[str, dict] = {}
                for c in scored:
                    key = json.dumps([c["links"], c["your_total"]], sort_keys=True)
                    entry = entries.setdefault(
                        key, {"share": c["your_total"] / max(c["max_total"], 1), "names": []}
                    )
                    entry["names"].append(c["name"])
                ranked = sorted(entries.values(), key=lambda e: -e["share"])
                if not ranked:
                    continue
                cutoff = ranked[math.ceil(len(ranked) / 2) - 1]["share"]
                print("=" * 70)
                print(f"{programme['title'][:60]}  ({len(ranked)} scored entries)")
                for e in ranked:
                    tier = "Merit" if e["share"] >= cutoff else "Completion"
                    print(f"  {tier:<10} {e['share'] * 100:5.1f}%  {', '.join(e['names'])}")
                    for name in e["names"]:
                        p = people[name]
                        p["on"].append(f"{programme['title'][:28]}={tier}")
                        if tier == "Merit":
                            p["tier"] = "Merit"
                if unscored:
                    print(f"  submitted but NOT scored yet: {', '.join(unscored)}")
    print("\n" + "=" * 70)
    merit = sorted(n for n, p in people.items() if p["tier"] == "Merit")
    comp = sorted(n for n, p in people.items() if p["tier"] == "Completion")
    print(f"PEOPLE: {len(people)}  Merit: {len(merit)}  Completion: {len(comp)}")
    print("MERIT: " + "; ".join(merit))
    print("COMPLETION: " + "; ".join(comp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
