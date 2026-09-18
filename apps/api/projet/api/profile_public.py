"""The public profile — FR-1201, /p/{handle}.

Reachable with no session, by design: the whole point is that someone who was
never in the room can read it. Consent is enforced here at the query layer,
not by the frontend choosing not to render something:

  * the route answers 404 unless Person.public is set — a profile is public
    by an explicit act, never by having enough evidence to be worth showing.
  * a ProjectEntry with visible=False is left out entirely.
  * a project's links are left out unless its own artifact_visibility says so
    — the consent given to one company for one week of judging was never
    consent to a public, indefinite audience, and it does not carry over.

Nothing here carries a score, a rank or a referral flag — same as the
participant's own portfolio view, because this is the same evidence shown to
a second audience, not a different, looser one.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.db import get_session
from projet.models import Company, Person, Programme
from projet.models.enums import ArtifactVisibility
from projet.services.closeout import credentials_for
from projet.services.profile import capability_rollup, published_testimonials_for
from projet.services.projects import entries_for

router = APIRouter(prefix="/p", tags=["public profile"])


class PublicAttestedSkill(BaseModel):
    name: str
    type: str
    attesters: list[str]
    programme_count: int


class PublicCapability(BaseModel):
    name: str
    slug: str
    summary: str
    skills: list[PublicAttestedSkill]
    programme_count: int
    attester_count: int


class PublicProjectLink(BaseModel):
    kind: str
    url: str
    label: str | None


class PublicProjectEntry(BaseModel):
    verified: bool
    kind: str
    title: str
    organisation_name: str | None
    started_at: date | None
    ended_at: date | None
    problem: str | None
    approach: str | None
    contribution: list[str]
    outcome: str | None
    links: list[PublicProjectLink]


class PublicCredential(BaseModel):
    type: str
    programme: str
    company: str
    issued_at: datetime
    verify_code: str


class PublicTestimonial(BaseModel):
    body: str
    author_name: str | None
    author_title: str | None
    company: str
    programme: str
    published_at: datetime | None


class PublicProfile(BaseModel):
    name: str
    handle: str
    headline: str | None
    bio: str | None
    location: str | None
    capabilities: list[PublicCapability]
    projects: list[PublicProjectEntry]
    credentials: list[PublicCredential]
    testimonials: list[PublicTestimonial]
    # Verified and self-declared work are counted apart on purpose: a count
    # that blended them would let self-declared volume read as evidence this
    # platform stands behind, which is exactly the thing verified-first
    # ordering exists to prevent.
    verified_project_count: int
    self_declared_project_count: int
    programmes_completed: int


def _project_out(entry) -> PublicProjectEntry:  # type: ignore[no-untyped-def]
    links = (
        []
        if entry.artifact_visibility is ArtifactVisibility.PRIVATE
        else [
            PublicProjectLink(kind=link.kind.value, url=link.url, label=link.label)
            for link in entry.links
        ]
    )
    return PublicProjectEntry(
        verified=entry.verified,
        kind=entry.kind.value,
        title=entry.title,
        organisation_name=entry.organisation_name,
        started_at=entry.started_at,
        ended_at=entry.ended_at,
        problem=entry.problem,
        approach=entry.approach,
        contribution=list(entry.contribution or []),
        outcome=entry.outcome,
        links=links,
    )


@router.get("/{handle}", response_model=PublicProfile)
def get_public_profile(
    handle: str,
    db: Session = Depends(get_session),
) -> PublicProfile:
    person = db.scalar(select(Person).where(Person.handle == handle))
    # Same 404 whether the handle does not exist or the profile is off — a
    # handle that resolves only when public would leak which handles exist.
    if person is None or not person.public:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile at that handle.")

    capabilities = [
        PublicCapability(
            name=rollup.name,
            slug=rollup.slug,
            summary=rollup.summary,
            skills=[
                PublicAttestedSkill(
                    name=item.name,
                    type=item.type.value,
                    attesters=item.attesters,
                    programme_count=len(item.programme_ids),
                )
                for item in rollup.skills
            ],
            programme_count=rollup.programme_count,
            attester_count=rollup.attester_count,
        )
        for rollup in capability_rollup(db, person.id)
    ]

    entries = entries_for(db, person.id)
    projects = [_project_out(entry) for entry in entries]
    verified_count = sum(1 for entry in entries if entry.verified)

    credentials: list[PublicCredential] = []
    for credential in credentials_for(db, person.id):
        programme = db.get(Programme, credential.programme_id)
        company = db.get(Company, programme.company_id) if programme else None
        credentials.append(
            PublicCredential(
                type=credential.type.value,
                programme=programme.title if programme else "",
                company=company.name if company else "",
                issued_at=credential.issued_at,
                verify_code=credential.verify_code,
            )
        )

    testimonials = [
        PublicTestimonial(
            body=row.Testimonial.body,
            author_name=row.CompanyUser.name,
            author_title=row.CompanyUser.title,
            company=row.Company.name,
            programme=row.Programme.title,
            published_at=row.Testimonial.published_at,
        )
        for row in published_testimonials_for(db, person.id)
    ]

    return PublicProfile(
        name=person.name,
        handle=person.handle or handle,
        headline=person.headline,
        bio=person.bio,
        location=person.location,
        capabilities=capabilities,
        projects=projects,
        credentials=credentials,
        testimonials=testimonials,
        verified_project_count=verified_count,
        self_declared_project_count=len(entries) - verified_count,
        programmes_completed=len({c.programme_id for c in credentials_for(db, person.id)}),
    )
