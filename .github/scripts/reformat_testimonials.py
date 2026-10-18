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
# Team members to add to the Re: line, and whether to redo letters already signed.
EXTRA = [n.strip() for n in (os.environ.get("EXTRA_NAMES") or "").split(",") if n.strip()]
INCLUDE_SIGNED = os.environ.get("INCLUDE_SIGNED") == "1"
MATCH = (os.environ.get("COMPANY_MATCH") or "bluenexus").lower()
# Left empty, the sign-off falls back to the signed-in account's own details.
SIGNER = os.environ.get("SIGNER_NAME") or ""
TITLE = os.environ.get("SIGNER_TITLE") or ""
COMPANY = os.environ.get("SIGNER_COMPANY") or ""
DETAILS = os.environ.get("COMPANY_DETAILS") or ""

CLOSING = re.compile(
    r"^(sincerely|yours sincerely|yours faithfully|best regards|kind regards|warm regards|regards)\b",
    re.IGNORECASE,
)


def split_letter(body: str, participant: str) -> tuple[list[str], str, str]:
    """Names from the salutation, the body without it, and what was cut off the end."""
    lines = body.strip().splitlines()
    names: list[str] = [participant]
    # The old letters carry their own heading (company, "Letter of appreciation",
    # date, "Presented to") above the salutation; the letterhead replaces it.
    dear = next(
        (i for i, line in enumerate(lines[:10]) if re.match(r"^\s*dear\b", line, re.IGNORECASE)),
        None,
    )
    if dear is not None:
        salutation = re.sub(r"^\s*dear\s+", "", lines[dear], flags=re.IGNORECASE).strip(" ,:")
        for raw in re.split(r"\s*(?:&|,|\band\b)\s*", salutation):
            name = raw.strip()
            if not name:
                continue
            # The salutation can misspell the person we already have.
            if difflib.SequenceMatcher(None, name.lower(), participant.lower()).ratio() >= 0.7:
                continue
            names.append(name)
        lines = lines[dear + 1 :]
    cut = len(lines)
    for index, line in enumerate(lines):
        if CLOSING.match(line.strip()):
            cut = index
            break
    kept = "\n".join(lines[:cut]).strip()
    dropped = "\n".join(lines[cut:]).strip()
    return names, kept, dropped


def details_from(dropped: str, company: str) -> str:
    """The address block under the sign-off: what follows the last company-name line."""
    lines = [line.strip() for line in dropped.splitlines()]
    starts = [i for i, line in enumerate(lines) if company and line.lower() == company.lower()]
    if not starts:
        return DETAILS
    block = [line for line in lines[starts[-1] + 1 :] if line]
    return "\n".join(block) or DETAILS


def main() -> int:
    if not PASSWORD:
        print("COMPANY_PASSWORD is not set.", file=sys.stderr)
        return 2
    emails = {item["email"] for item in CHALLENGES if MATCH in item["email"].lower()}
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
                    if t.get("own_file") or not t.get("published_at"):
                        continue
                    if t.get("signed") and not INCLUDE_SIGNED:
                        continue
                    names, body, dropped = split_letter(t["body"], card["name"])
                    names += [n for n in EXTRA if n not in names]
                    print("=" * 70)
                    print(f"{card['name']}  |  {programme['title'][:50]}")
                    ctx = client.get(f"{base}/context").json()
                    signer = SIGNER or ctx["author_name"]
                    title = TITLE or ctx["author_title"]
                    company = COMPANY or ctx["company_name"]
                    details = details_from(dropped, company)
                    print("-- BEFORE --")
                    print(t["body"])
                    print("-- AFTER --")
                    print(f"Re: {', '.join(names)}")
                    print(body)
                    print(f"[from: {signer}, {title or '(no title)'}, {company}]")
                    print(f"[details: {details}]")
                    print(f"[cut from the end: {dropped or 'nothing'}]")
                    if not APPLY:
                        continue
                    put = client.put(
                        base,
                        json={
                            "body": body,
                            "publish": False,
                            "recipients": names,
                            "signoff_name": signer,
                            "signoff_title": title,
                            "signoff_company": company,
                            "company_details": details,
                        },
                    )
                    sign = client.post(f"{base}/sign", json={"typed": True, "confirm": True})
                    print(f">> saved {put.status_code}, signed {sign.status_code}")
    print("\nDry run only. Nothing changed." if not APPLY else "\nApplied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
