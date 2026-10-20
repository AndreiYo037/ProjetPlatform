"""Put people's real names on the Re: line of every testimonial.

Some letters name a person by their platform username (Leejunyuan125,
E1591814) or by first name only. This sets each letter's recipients to the full
names. Only the Re: line changes: the body and the sign-off are left as saved,
and the letter is signed again with the typed name because a change voids the
signature. Dry run unless APPLY=1.
"""

from __future__ import annotations

import os
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
APPLY = os.environ.get("APPLY") == "1"

# Keyed by the name the platform shows for the participant. Real names come
# from the Google-form sign-ups.
NAMES: dict[str, list[str]] = {
    "Thriti Das": ["Thriti Das", "Tori Xiao"],
    "Jade Yap": ["Jade Yap", "Siaw Min En Alena"],
    "Lin Yu Wei": ["Lin Yu Wei", "Lee Seung Jun"],
    "W Hansel 2025": ["William Hansel", "Tan Wee Teck Alfonso", "Ngo Thuy Linh"],
    "Osby Angelo Pua De Leon": [
        "Osby Angelo Pua De Leon",
        "Kylie Khoo Hoi Yann",
        "Muhammad Abdul Rauf Bin Abdul Malik",
    ],
    "Ng Yu Hang (Mervin)": ["Ng Yu Hang"],
    "Warren Lee": ["Warren Lee"],
    "Leejunyuan125": ["Lee Jun Yuan", "Nadine Wielter Lim"],
    "E1591814": ["Zhang Jiayi", "Lee Jae Yan"],
    "Wang Jianan": ["Wang Jianan"],
    "Nathaniel Sim": ["Nathaniel Sim", "Audric Fuster"],
}


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
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
                pid = programme["id"]
                for card in client.get(f"/programmes/{pid}/submissions").json():
                    base = f"/programmes/{pid}/participants/{card['participant_id']}/testimonial"
                    t = client.get(base).json()
                    if not t or t.get("own_file"):
                        continue
                    want = NAMES.get(card["name"])
                    if want is None:
                        print(f"?? no names listed for {card['name']} (left alone)")
                        continue
                    have = t.get("recipients") or []
                    if have == want:
                        print(f"ok   {card['name']}: already {want}")
                        continue
                    if t.get("signed") and not t.get("signature_typed"):
                        print(f"skip {card['name']}: hand-drawn signature, not touching")
                        continue
                    print(f"fix  {card['name']}: {have} -> {want}")
                    if not APPLY:
                        continue
                    put = client.put(base, json={"body": t["body"], "publish": False, "recipients": want})
                    sign = client.post(f"{base}/sign", json={"typed": True, "confirm": True})
                    print(f"     saved {put.status_code}, signed {sign.status_code}")
    print("\nApplied." if APPLY else "\nDry run only. Nothing changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
