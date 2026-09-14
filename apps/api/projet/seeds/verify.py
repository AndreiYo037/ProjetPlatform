"""projet-verify-sources — fetch each registry source and stamp it.

Milestone 0's real work. The resource map names sources without URLs, so most
entries cannot be verified until a URL is filled in; this command reports what
is outstanding per role and verifies whatever it can reach.

A role is never blocked from activation by this — blocking would hold every role —
but the readiness report is what tells admin whether a role's data pack is real.
"""

from __future__ import annotations

import argparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.db import get_sessionmaker
from projet.models import DataPackResource, Role
from projet.models.base import utcnow
from projet.models.enums import VerificationStatus


def verify_source(client: httpx.Client, resource: DataPackResource) -> VerificationStatus:
    if not resource.url_or_storage_key:
        return VerificationStatus.UNVERIFIED
    try:
        response = client.head(resource.url_or_storage_key, follow_redirects=True, timeout=15)
        if response.status_code >= 400:
            # Plenty of statistics portals refuse HEAD but serve GET.
            response = client.get(resource.url_or_storage_key, follow_redirects=True, timeout=20)
        ok = response.status_code < 400
    except httpx.HTTPError:
        ok = False

    resource.access_status = "ok" if ok else "unreachable"
    if ok:
        resource.verification_status = VerificationStatus.VERIFIED
        resource.last_verified_at = utcnow()
    else:
        resource.verification_status = VerificationStatus.FAILED
    return resource.verification_status


def readiness_report(session: Session) -> list[dict]:
    """Per role: how much of its data pack is actually validated."""
    rows = []
    for role in session.scalars(select(Role).order_by(Role.sort_order)):
        sources = list(
            session.scalars(select(DataPackResource).where(DataPackResource.role_id == role.id))
        )
        verified = [s for s in sources if s.verification_status == VerificationStatus.VERIFIED]
        missing_url = [s for s in sources if not s.url_or_storage_key]
        rows.append(
            {
                "role": role.name,
                "sources": len(sources),
                "verified": len(verified),
                "missing_url": len(missing_url),
                "ready": bool(sources) and len(verified) == len(sources),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify public data pack sources.")
    parser.add_argument("--report-only", action="store_true", help="do not fetch anything")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as session:
        if not args.report_only:
            pending = list(
                session.scalars(
                    select(DataPackResource)
                    .where(DataPackResource.url_or_storage_key.is_not(None))
                    .where(DataPackResource.verification_status != VerificationStatus.VERIFIED)
                )
            )
            if pending:
                with httpx.Client() as client:
                    for resource in pending:
                        status = verify_source(client, resource)
                        print(f"  {status.value:<11} {resource.label}")
                session.commit()
            else:
                print("nothing to fetch: no source has a URL yet.")

        rows = readiness_report(session)

    ready = [r for r in rows if r["ready"]]
    total_sources = sum(r["sources"] for r in rows)
    verified = sum(r["verified"] for r in rows)
    print(f"\n{len(ready)}/{len(rows)} roles have a fully validated data pack")
    print(f"{verified}/{total_sources} source entries verified")
    outstanding = sum(r["missing_url"] for r in rows)
    if outstanding:
        print(f"{outstanding} entries still have no URL — that is the Milestone 0 work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
