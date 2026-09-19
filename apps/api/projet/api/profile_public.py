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
from projet.models import Person
from projet.models.enums import ArtifactVisibility
from projet.services.closeout import credentials_for
from projet.services.profile import (
    attested_skills,
    endorsements_for,
    published_testimonials_for,
    sync_person_skills_from_tags,
)
from projet.services.projects import entries_for
from projet.storage import sign_key

router = APIRouter(prefix="/p", tags=["public profile"])


class PublicAttestedSkill(BaseModel):
    name: str
    type: str
    attesters: list[str]
    programme_count: int


class PublicProjectLink(BaseModel):
    """A URL, or a signed expiring link to an uploaded file."""

    url: str
    filename: str | None
    label: str | None


class PublicProjectEntry(BaseModel):
    verified: bool
    title: str
    associated_experience: str | None
    started_at: date | None
    ended_at: date | None
    ongoing: bool
    description: str | None
    links: list[PublicProjectLink]
    skills: list[str]


class PublicCredential(BaseModel):
    company: str
    programme: str
    skills: list[str]
    attesters: list[str]
    start_at: datetime | None
    ended_at: datetime | None


class PublicTestimonial(BaseModel):
    body: str
    author_name: str | None
    author_title: str | None
    company: str
    programme: str
    pdf_url: str | None
    published_at: datetime | None


class PublicProfile(BaseModel):
    name: str
    handle: str
    headline: str | None
    bio: str | None
    location: str | None
    # Flat, one row per skill: grouping onto capability axes made one judge's
    # single tag appear under two headings and read as two endorsements.
    skills: list[PublicAttestedSkill]
    attester_count: int
    programme_count: int
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


def _public_link(link) -> PublicProjectLink | None:  # type: ignore[no-untyped-def]
    if link.storage_key:
        # Signed and expiring even here. A public profile makes the file
        # reachable; it does not make its storage key a permanent address.
        return PublicProjectLink(
            url=f"/files/{link.storage_key}?sig={sign_key(link.storage_key)}",
            filename=link.filename,
            label=link.label or link.filename,
        )
    if link.url:
        return PublicProjectLink(url=link.url, filename=None, label=link.label)
    return None


def _project_out(entry) -> PublicProjectEntry:  # type: ignore[no-untyped-def]
    # The consent gate, applied once, here: the description is not the
    # confidential part, but the work itself can be.
    links: list[PublicProjectLink] = []
    if entry.artifact_visibility is not ArtifactVisibility.PRIVATE:
        links = [out for out in (_public_link(link) for link in entry.links) if out is not None]

    return PublicProjectEntry(
        verified=entry.verified,
        title=entry.title,
        associated_experience=entry.associated_experience,
        started_at=entry.started_at,
        ended_at=entry.ended_at,
        ongoing=entry.ongoing,
        description=entry.description,
        links=links,
        skills=sorted({ps.skill.name for ps in entry.skills}),
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

    sync_person_skills_from_tags(db, person.id)
    db.commit()
    evidence = attested_skills(db, person.id)
    skills = [
        PublicAttestedSkill(
            name=item.name,
            type=item.type.value,
            attesters=item.attesters,
            programme_count=len(item.programme_ids),
        )
        for item in evidence.skills
    ]

    entries = entries_for(db, person.id)
    projects = [_project_out(entry) for entry in entries]
    verified_count = sum(1 for entry in entries if entry.verified)

    credentials = [
        PublicCredential(
            company=row.company,
            programme=row.programme,
            skills=row.skills,
            attesters=row.attesters,
            start_at=row.start_at,
            ended_at=row.ended_at,
        )
        for row in endorsements_for(db, person.id)
    ]

    testimonials = [
        PublicTestimonial(
            body=row.Testimonial.body,
            author_name=row.CompanyUser.name,
            author_title=row.CompanyUser.title,
            company=row.Company.name,
            programme=row.Programme.title,
            pdf_url=(
                f"/files/{row.Testimonial.pdf_storage_key}?sig={sign_key(row.Testimonial.pdf_storage_key)}"
                if row.Testimonial.pdf_storage_key
                else None
            ),
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
        skills=skills,
        attester_count=evidence.attester_count,
        programme_count=evidence.programme_count,
        projects=projects,
        credentials=credentials,
        testimonials=testimonials,
        verified_project_count=verified_count,
        self_declared_project_count=len(entries) - verified_count,
        programmes_completed=len({c.programme_id for c in credentials_for(db, person.id)}),
    )
