"""Reformat already-published BlueNexus testimonials into the standard letter.

Those letters were typed with their own "Dear ..." salutation and, sometimes,
their own sign-off, before the letter became a form. This moves the parts into
the boxes the letter prints from (names on the Re: line, sign-off name and
company details) and signs with the typed name, as a manual fallback.

Dry run by default: prints each letter before and after and changes nothing.
Set APPLY=1 to write and sign. ONLY narrows it to participants whose name
contains that text.
"""

from __future__ import annotations

import difflib
import os
import re
import sys

import httpx

from create_hacknhire_challenges import API_BASE, CHALLENGES

PASSWORD = os.environ.get("COMPANY_PASSWORD")
APPLY = os.environ.get("APPLY") == "1"
ONLY = (os.environ.get("ONLY") or "").strip().lower()
SIGNER = os.environ.get("SIGNER_NAME") or "Jeffrey Chen"
TITLE = os.environ.get("SIGNER_TITLE") or ""
COMPANY = os.environ.get("SIGNER_COMPANY") or "BlueNexus Technologies Pte. Ltd."
DETAILS = os.environ.get("COMPANY_DETAILS") or "51 Goldhill Plaza, #07-07, Singapore 308900"

CLOSING = re.compile(
    r"^(sincerely|yours sincerely|yours faithfully|best regards|kind regards|warm regards|regards)\b",
    re.IGNORECASE,
)


def split_letter(body: str, participant: str) -> tuple[list[str], str, str]:
    """Names from the salutation, the body without it, and what was cut off the end."""
    lines = body.strip().splitlines()
    names: list[str] = [participant]
    if lines and re.match(r"^\s*dear\b", lines[0], re.IGNORECASE):
        salutation = re.sub(r"^\s*dear\s+", "", lines[0], flags=re.IGNORECASE).strip(" ,:")
        for raw in re.split(r"\s*(?:&|,|\band\b)\s*", salutation):
            name = raw.strip()
            if not name:
                continue
            # The salutation can misspell the person we already have.
            if difflib.SequenceMatcher(None, name.lower(), participant.lower()).ratio() >= 0.7:
                continue
            names.append(name)
        lines = lines[1:]
    cut = len(lines)
    for index, line in enumerate(lines):
        if CLOSING.match(line.strip()):
            cut = index
            break
    kept = "\n".join(lines[:cut]).strip()
    dropped = "\n".join(lines[cut:]).strip()
    return names, kept, dropped


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    emails = {item["email"] for item in CHALLENGES if "bluenexus" in item["email"]}
    for email in sorted(emails):
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
                    if ONLY and ONLY not in card["name"].lower():
                        continue
                    base = f"/programmes/{pid}/participants/{card['participant_id']}/testimonial"
                    resp = client.get(base)
                    if resp.status_code != 200 or not resp.json():
                        continue
                    t = resp.json()
                    if t.get("own_file") or not t.get("published_at") or t.get("signed"):
                        continue
                    names, body, dropped = split_letter(t["body"], card["name"])
                    print("=" * 70)
                    print(f"{card['name']}  |  {programme['title'][:50]}")
                    print("-- BEFORE --")
                    print(t["body"])
                    print("-- AFTER --")
                    print(f"Re: {', '.join(names)}")
                    print(body)
                    print(f"[from: {SIGNER}, {TITLE or '(no title)'}, {COMPANY}]")
                    print(f"[details: {DETAILS}]")
                    print(f"[cut from the end: {dropped or 'nothing'}]")
                    if not APPLY:
                        continue
                    put = client.put(
                        base,
                        json={
                            "body": body,
                            "publish": False,
                            "recipients": names,
                            "signoff_name": SIGNER,
                            "signoff_title": TITLE,
                            "signoff_company": COMPANY,
                            "company_details": DETAILS,
                        },
                    )
                    sign = client.post(f"{base}/sign", json={"typed": True, "confirm": True})
                    print(f">> saved {put.status_code}, signed {sign.status_code}")
    print("\nDry run only. Nothing changed." if not APPLY else "\nApplied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
