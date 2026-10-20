"""Plan, and optionally issue, the Hack n Hire certificates for closed challenges.

One certificate per team with every member's full name printed together. Merit
for the top half of each challenge (top 10 if a challenge has 20 or more
scored teams), Completion for the rest, and Jade Yap's team gets a 3rd Place
Merit. Plan only unless APPLY=1. Nothing is emailed.

TEAMS maps the name the platform shows for the submitting participant to the
real names printed on the certificate, and to teammates who have their own
participant record so they can see the certificate too.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
APPLY = os.environ.get("APPLY") == "1"
EVENT = "Hack n Hire 2026"
EVENT_DATE = "17 October 2026"

# key: the submitting participant as the platform names them.
TEAMS: dict[str, dict] = {
    # BlueNexus: Water Treatment
    "Osby Angelo Pua De Leon": {
        "names": [
            "Osby Angelo Pua De Leon",
            "Kylie Khoo Hoi Yann",
            "Muhammad Abdul Rauf Bin Abdul Malik",
        ],
        "extra": ["Kylie Khoo"],
    },
    "Leejunyuan125": {
        "names": ["Lee Jun Yuan", "Nadine Wielter Lim"],
        "extra": ["Lee Jun Yuan", "Nadine Wielter Lim"],
    },
    "E1591814": {"names": ["Zhang Jiayi", "Lee Jae Yan"], "extra": ["Lee Jae Yan"]},
    "Warren Lee": {"names": ["Warren Lee"], "extra": ["Warren Lee"]},
    "Ng Yu Hang (Mervin)": {"names": ["Ng Yu Hang"], "extra": []},
    # BlueNexus: Sustainability
    "Thriti Das": {"names": ["Thriti Das", "Tori Xiao"], "extra": ["Tori Xiao"]},
    "Lin Yu Wei": {"names": ["Lin Yu Wei", "Lee Seung Jun"], "extra": []},
    "Jade Yap": {
        "names": ["Jade Yap", "Siaw Min En Alena"],
        "extra": [],
        "place_label": "3rd Place",
    },
    "W Hansel 2025": {
        "names": ["William Hansel", "Tan Wee Teck Alfonso", "Ngo Thuy Linh"],
        "extra": ["Tan wee teck alfonso"],
    },
    # beez-fm
    "Wang Jianan": {"names": ["Wang Jianan"], "extra": []},
    "Nathaniel Sim": {"names": ["Nathaniel Sim", "Audric Fuster"], "extra": ["Audric Fuster"]},
    "Kotipalli Bhavya Sri Sai": {"names": ["Kotipalli Bhavya Sri Sai"], "extra": []},
    "Gattu Sai Ganesh Santhosh": {"names": ["Gattu Sai Ganesh Santhosh"], "extra": []},
}

# Teams that applied and teams that submitted, per challenge (title starts with).
# Estimates from the sign-up lists: check them in the plan before issuing.
COUNTS: dict[str, tuple[int, int]] = {
    "Improving Water Treatment": (8, 5),
    "Measuring and Communicating": (9, 4),
    "Visualising Technology Fit": (12, 6),
}


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    for email in sorted({i["email"] for i in CHALLENGES}):
        with httpx.Client(base_url=API_BASE, timeout=120) as client:
            login = client.post(
                "/auth/login",
                json={"actor_type": "company_user", "email": email, "password": PASSWORD},
            )
            if login.status_code != 200:
                print(f"!! login failed for {email}: {login.status_code}")
                return 1
            for programme in client.get("/programmes").json():
                if programme.get("status") != "complete":
                    continue
                pid = programme["id"]
                cards = client.get(f"/programmes/{pid}/submissions").json()
                by_name: dict[str, list[str]] = {}
                for card in cards:
                    by_name.setdefault(card["name"], []).append(card["participant_id"])
                teams = []
                for key, spec in TEAMS.items():
                    ids = by_name.get(key)
                    if not ids:
                        continue
                    extra = [i for n in spec["extra"] for i in by_name.get(n, []) if i not in ids]
                    item = {
                        "participant_id": ids[0],
                        "names": spec["names"],
                        "extra_participant_ids": extra,
                    }
                    if spec.get("place_label"):
                        item["place_label"] = spec["place_label"]
                    teams.append(item)
                body: dict = {"teams": teams, "event_name": EVENT, "event_date": EVENT_DATE}
                for prefix, (applied, submitted) in COUNTS.items():
                    if programme["title"].startswith(prefix):
                        body["applied_teams"], body["submitted_teams"] = applied, submitted
                print("=" * 70)
                print(f"{programme['title'][:60]}  (applied {body.get('applied_teams')}, "
                      f"submitted {body.get('submitted_teams')})")
                plan = client.post(f"/programmes/{pid}/certificates/plan", json=body)
                if plan.status_code != 200:
                    print(f"  plan failed {plan.status_code}: {plan.text[:200]}")
                    continue
                for row in plan.json():
                    label = row["place_label"] or row["tier"].capitalize()
                    joint = "joint " if row["joint"] else ""
                    print(f"  {label:<11} rank {joint}{row['rank']}/{row['entries']} "
                          f"{row['share_pct']:5.1f}%  {', '.join(row['names'])}")
                if APPLY:
                    issued = client.post(f"/programmes/{pid}/certificates/issue", json=body)
                    print(f"  >> issued {issued.status_code}: "
                          f"{len(issued.json()) if issued.status_code == 200 else issued.text[:200]}")
    print("\nIssued." if APPLY else "\nPlan only. Nothing issued.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
