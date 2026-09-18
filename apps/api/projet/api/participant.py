"""The participant's own view (FR-500, FR-700, FR-800).

Everything here is scoped to the signed-in participant. A participant-facing
schema has no field for a score, a ranking or a referral flag, so section 8's
rule holds by construction rather than by remembering to omit them (FR-1004).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import require_participant
from projet.db import get_session
from projet.models import (
    Company,
    JudgingSession,
    Participant,
    Person,
    Post,
    Programme,
    ProjectEntry,
    ProjectLink,
    Role,
    RoleTemplate,
    RubricCriterion,
    SubmissionLink,
    Thread,
)
from projet.models.base import utcnow
from projet.models.enums import ArtifactVisibility, ProgrammeStatus, SubmissionSlot
from projet.services.auth import Actor
from projet.services.closeout import credentials_for
from projet.services.data_pack import released_resources, resource_url
from projet.services.messaging import (
    mark_read,
    unacknowledged,
    unread_counts,
    visible_threads,
)
from projet.services.profile import capability_rollup, published_testimonials_for
from projet.services.projects import (
    ProjectError,
    add_link,
    attach_file,
    create_entry,
    delete_entry,
    entries_for,
    remove_link,
    seed_from_participant,
    set_skills,
    update_entry,
)
from projet.services.skills import options_for_role
from projet.services.submission import (
    SubmissionError,
    clear_link,
    is_locked,
    recheck,
    set_link,
    set_upload,
    submission_for_participant,
)
from projet.storage import sign_key

router = APIRouter(prefix="/me", tags=["participant"])

MAX_SUBMISSION_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_SUBMISSION_UPLOAD_TYPES = {"application/pdf"}


class ProfileOut(BaseModel):
    name: str
    email: str
    organisation: str | None = None
    year_course: str | None = None
    job_title: str | None = None
    phone: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    organisation: str | None = Field(default=None, max_length=300)
    year_course: str | None = Field(default=None, max_length=300)
    job_title: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=60)


def _person(db: Session, actor: Actor) -> Person:
    person = db.get(Person, actor.id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    return person


def _profile_out(person: Person) -> ProfileOut:
    return ProfileOut(
        name=person.name,
        email=person.contact_email,
        organisation=person.organisation,
        year_course=person.year_course,
        job_title=person.job_title,
        phone=person.phone,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProfileOut:
    return _profile_out(_person(db, actor))


class AttestedSkill(BaseModel):
    name: str
    type: str
    # Who stands behind it. This is the entire difference between this and a
    # skill somebody typed into a box about themselves.
    attesters: list[str]
    programme_count: int


class CapabilityOut(BaseModel):
    name: str
    slug: str
    summary: str
    skills: list[AttestedSkill]
    programme_count: int
    attester_count: int


class CredentialOut(BaseModel):
    type: str
    programme: str
    company: str
    issued_at: datetime
    # The code is the credential. Carried here so the holder can give it to
    # someone who was never in the room.
    verify_code: str


class TestimonialCard(BaseModel):
    body: str
    author_name: str | None
    author_title: str | None
    company: str
    programme: str
    published_at: datetime | None


class Portfolio(BaseModel):
    """What the participant keeps (FR-1201).

    Deliberately separate from ProfileOut, which is the editable account. Nothing
    on this page is editable, because nothing on it is the participant's claim:
    every line was put there by a practitioner who watched them work.
    """

    name: str
    handle: str | None
    capabilities: list[CapabilityOut]
    credentials: list[CredentialOut]
    testimonials: list[TestimonialCard]
    programmes_completed: int


@router.get("/portfolio", response_model=Portfolio)
def get_portfolio(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> Portfolio:
    """Judge tags, credentials and testimonials, compounded across programmes.

    Scores are not here and cannot be: FR-1004 keeps them out of every
    participant-facing schema, so a rating never reaches the person rated even
    by accident. What they see is the evidence, not the arithmetic.
    """
    person = _person(db, actor)
    return _portfolio(db, person)


def _portfolio(db: Session, person: Person) -> Portfolio:
    capabilities = [
        CapabilityOut(
            name=rollup.name,
            slug=rollup.slug,
            summary=rollup.summary,
            skills=[
                AttestedSkill(
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

    credentials: list[CredentialOut] = []
    for credential in credentials_for(db, person.id):
        programme = db.get(Programme, credential.programme_id)
        company = db.get(Company, programme.company_id) if programme else None
        credentials.append(
            CredentialOut(
                type=credential.type.value,
                programme=programme.title if programme else "",
                company=company.name if company else "",
                issued_at=credential.issued_at,
                verify_code=credential.verify_code,
            )
        )

    rows = published_testimonials_for(db, person.id)
    testimonials = [
        TestimonialCard(
            body=row.Testimonial.body,
            author_name=row.CompanyUser.name,
            author_title=row.CompanyUser.title,
            company=row.Company.name,
            programme=row.Programme.title,
            published_at=row.Testimonial.published_at,
        )
        for row in rows
    ]

    return Portfolio(
        name=person.name,
        handle=person.handle,
        capabilities=capabilities,
        credentials=credentials,
        testimonials=testimonials,
        programmes_completed=len(
            {c.programme_id for c in credentials_for(db, person.id)}
        ),
    )


class ProjectLinkOut(BaseModel):
    """A URL or an uploaded file. `file_url` is a signed, expiring link and is
    only ever populated for a file."""

    id: uuid.UUID
    url: str | None
    filename: str | None
    file_url: str | None
    label: str | None


class ProjectSkillOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str


class ProjectEntryOut(BaseModel):
    """One project card.

    `verified` is the only thing on here the participant cannot set, and it is
    the thing the whole card is read against, so it is a field of its own.
    """

    id: uuid.UUID
    verified: bool
    title: str
    associated_experience: str | None
    started_at: date | None
    ended_at: date | None
    ongoing: bool
    description: str | None
    artifact_visibility: str
    visible: bool
    links: list[ProjectLinkOut]
    skills: list[ProjectSkillOut]


def _link_out(link: ProjectLink) -> ProjectLinkOut:
    return ProjectLinkOut(
        id=link.id,
        url=link.url,
        filename=link.filename,
        # Signed here rather than stored: the link expires, so a URL that
        # leaks stops working instead of becoming a permanent back door.
        file_url=(
            f"/files/{link.storage_key}?sig={sign_key(link.storage_key)}"
            if link.storage_key
            else None
        ),
        label=link.label,
    )


def _project_out(entry: ProjectEntry) -> ProjectEntryOut:
    return ProjectEntryOut(
        id=entry.id,
        verified=entry.verified,
        title=entry.title,
        associated_experience=entry.associated_experience,
        started_at=entry.started_at,
        ended_at=entry.ended_at,
        ongoing=entry.ongoing,
        description=entry.description,
        artifact_visibility=entry.artifact_visibility.value,
        visible=entry.visible,
        links=[_link_out(link) for link in entry.links],
        skills=[
            ProjectSkillOut(id=ps.skill_id, name=ps.skill.name, type=ps.skill.type.value)
            for ps in entry.skills
        ],
    )


@router.get("/projects", response_model=list[ProjectEntryOut])
def list_projects(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> list[ProjectEntryOut]:
    person = _person(db, actor)
    return [_project_out(entry) for entry in entries_for(db, person.id)]


@router.post(
    "/projects/from-participant/{participant_id}",
    response_model=ProjectEntryOut,
    status_code=status.HTTP_201_CREATED,
)
def seed_project(
    participant_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    """Start a case study from a programme they finished.

    The organisation, the dates and the brief come across already verified.
    The four narrative fields come across empty, because the account of the
    work is theirs to write and always was.
    """
    person = _person(db, actor)
    try:
        entry = seed_from_participant(db, person.id, participant_id)
    except ProjectError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.commit()
    db.refresh(entry)
    return _project_out(entry)


def _project_http_error(exc: ProjectError) -> HTTPException:
    """404 when the entry is not theirs, 400 when the edit is not allowed.

    A missing entry and someone else's entry answer identically, so the
    response cannot be used to learn that an entry exists.
    """
    missing = "No project" in str(exc) or "No link" in str(exc)
    code = status.HTTP_404_NOT_FOUND if missing else status.HTTP_400_BAD_REQUEST
    return HTTPException(code, str(exc))


class ProjectEntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    associated_experience: str | None = None
    started_at: date | None = None
    ended_at: date | None = None
    ongoing: bool = False
    description: str | None = None
    artifact_visibility: str = "private"


def _parse_visibility(value: str) -> ArtifactVisibility:
    try:
        return ArtifactVisibility(value)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown artifact visibility."
        ) from exc


def _project_http_error(exc: ProjectError) -> HTTPException:
    """404 when the entry is not theirs, 400 when the edit is not allowed.

    A missing entry and someone else's entry answer identically, so the
    response cannot be used to learn that an entry exists.
    """
    missing = "No project" in str(exc) or "No link" in str(exc)
    code = status.HTTP_404_NOT_FOUND if missing else status.HTTP_400_BAD_REQUEST
    return HTTPException(code, str(exc))


@router.post("/projects", response_model=ProjectEntryOut, status_code=status.HTTP_201_CREATED)
def add_project(
    payload: ProjectEntryCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    """Start a case study for work this platform never ran.

    Counted alongside the verified ones and always shown after them — the
    scope decision this whole feature turns on.
    """
    person = _person(db, actor)
    try:
        entry = create_entry(
            db,
            person.id,
            title=payload.title,
            associated_experience=payload.associated_experience,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            ongoing=payload.ongoing,
            description=payload.description,
            artifact_visibility=_parse_visibility(payload.artifact_visibility),
        )
    except ProjectError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.commit()
    db.refresh(entry)
    return _project_out(entry)


class ProjectEntryUpdate(BaseModel):
    """Every field optional; only the ones sent are changed.

    A verified entry accepts the description and consent fields and rejects
    the rest with a named error (see `update_entry`) — never a silent no-op on
    a field the request thought it was changing.
    """

    title: str | None = Field(default=None, min_length=1, max_length=300)
    associated_experience: str | None = None
    started_at: date | None = None
    ended_at: date | None = None
    ongoing: bool | None = None
    description: str | None = None
    artifact_visibility: str | None = None
    visible: bool | None = None


@router.patch("/projects/{entry_id}", response_model=ProjectEntryOut)
def edit_project(
    entry_id: uuid.UUID,
    payload: ProjectEntryUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    person = _person(db, actor)
    changes = payload.model_dump(exclude_unset=True)
    if "artifact_visibility" in changes:
        changes["artifact_visibility"] = _parse_visibility(changes["artifact_visibility"])
    try:
        entry = update_entry(db, person.id, entry_id, changes)
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()
    db.refresh(entry)
    return _project_out(entry)


@router.delete("/projects/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(
    entry_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> None:
    person = _person(db, actor)
    try:
        delete_entry(db, person.id, entry_id)
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()


class ProjectLinkCreate(BaseModel):
    url: str = Field(min_length=1)
    label: str | None = None


@router.post(
    "/projects/{entry_id}/links",
    response_model=ProjectEntryOut,
    status_code=status.HTTP_201_CREATED,
)
def add_project_link(
    entry_id: uuid.UUID,
    payload: ProjectLinkCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    person = _person(db, actor)
    try:
        add_link(db, person.id, entry_id, url=payload.url, label=payload.label)
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()
    entry = db.get(ProjectEntry, entry_id)
    assert entry is not None
    return _project_out(entry)


@router.post(
    "/projects/{entry_id}/files",
    response_model=ProjectEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_file(
    entry_id: uuid.UUID,
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    """Attach the work itself, for work that does not live at a URL.

    Stored privately and reachable only through an expiring signed link, and
    only when this project's own consent setting allows it.
    """
    person = _person(db, actor)
    data = await file.read()
    try:
        link = attach_file(
            db,
            person.id,
            entry_id,
            filename=file.filename or "attachment",
            content_type=file.content_type,
            data=data,
        )
        if label and label.strip():
            link.label = label.strip()
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()
    entry = db.get(ProjectEntry, entry_id)
    assert entry is not None
    return _project_out(entry)


@router.delete("/projects/{entry_id}/links/{link_id}", response_model=ProjectEntryOut)
def remove_project_link(
    entry_id: uuid.UUID,
    link_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    person = _person(db, actor)
    try:
        remove_link(db, person.id, entry_id, link_id)
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()
    entry = db.get(ProjectEntry, entry_id)
    assert entry is not None
    return _project_out(entry)


class ProjectSkillsUpdate(BaseModel):
    skill_ids: list[uuid.UUID]


@router.put("/projects/{entry_id}/skills", response_model=ProjectEntryOut)
def set_project_skills(
    entry_id: uuid.UUID,
    payload: ProjectSkillsUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProjectEntryOut:
    """Tag what a self-declared project used.

    Never reachable for a verified entry: what it demonstrated is for a judge
    to attest, not for the participant to claim, and this is the boundary
    that keeps the two apart.
    """
    person = _person(db, actor)
    try:
        entry = set_skills(db, person.id, entry_id, payload.skill_ids)
    except ProjectError as exc:
        raise _project_http_error(exc) from exc
    db.commit()
    db.refresh(entry)
    return _project_out(entry)


class SkillOptionOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str


@router.get("/skills/options", response_model=list[SkillOptionOut])
def project_skill_options(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> list[SkillOptionOut]:
    """The whole taxonomy for the self-declared skill drawer.

    No role to rank against here — a self-declared project has none — so
    every skill is offered on equal footing and reached by typing, same as
    the judge's picker with an empty template (FR-903b).
    """
    return [
        SkillOptionOut(id=ranked.skill.id, name=ranked.skill.name, type=ranked.skill.type.value)
        for ranked in options_for_role(db, None)
    ]


@router.patch("/profile", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> ProfileOut:
    person = _person(db, actor)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Name is required.")
        person.name = name
    if payload.organisation is not None:
        person.organisation = payload.organisation.strip() or None
    if payload.year_course is not None:
        person.year_course = payload.year_course.strip() or None
    if payload.job_title is not None:
        person.job_title = payload.job_title.strip() or None
    if payload.phone is not None:
        person.phone = payload.phone.strip() or None
    db.commit()
    db.refresh(person)
    return _profile_out(person)


class SlotOut(BaseModel):
    slot: str
    drive_url: str | None
    access_status: str
    filename: str | None
    file_url: str | None = None
    message: str | None = None


class SubmissionOut(BaseModel):
    status: str
    locked: bool
    submitted_at: datetime | None
    slots: list[SlotOut]


class ThreadSummary(BaseModel):
    id: uuid.UUID
    type: str
    title: str | None
    pinned: bool
    requires_ack: bool
    acknowledged: bool
    status: str
    unread: int
    reply_count: int
    created_at: datetime


class DataPackEntry(BaseModel):
    label: str
    url: str | None
    provenance: str
    licence: str | None = None
    # Marked so the dashboard can say it out loud. The acknowledgement is the
    # gate; the tag is what stops someone forwarding it without thinking.
    confidential: bool = False


class CriterionPublic(BaseModel):
    slot: int
    name: str
    anchor_5: str | None
    anchor_3: str | None
    anchor_1: str | None


class ProgrammeCard(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    role: str
    status: str
    problem_statement: str | None
    deliverable: str
    start_at: datetime | None
    submit_deadline_at: datetime | None
    timezone: str


class JudgingSlot(BaseModel):
    starts_at: datetime
    location_or_meet_link: str | None
    run_order: int | None


class Dashboard(BaseModel):
    """FR-501 to FR-507 — what do I do, by when, and where."""

    provisioning: bool
    programme: ProgrammeCard
    submission: SubmissionOut | None
    judging: JudgingSlot | None
    criteria: list[CriterionPublic]
    data_pack: list[DataPackEntry]
    threads: list[ThreadSummary]
    blocking_acknowledgements: list[ThreadSummary]


def _participant(db: Session, actor: Actor) -> Participant:
    """The signed-in person's current participation.

    A person can have several across cohorts; the live one wins, and the most
    recent otherwise, so a returning participant lands on what they are doing
    now rather than something from last year.
    """
    live = (
        select(Participant)
        .join(Programme, Participant.programme_id == Programme.id)
        .where(Participant.person_id == actor.id)
        .where(Programme.status.not_in([ProgrammeStatus.COMPLETE]))
        .order_by(Programme.start_at.desc().nullslast())
    )
    participant = db.scalars(live).first()
    if participant is None:
        participant = db.scalars(
            select(Participant)
            .where(Participant.person_id == actor.id)
            .order_by(Participant.created_at.desc())
        ).first()
    if participant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not on a programme yet.")
    return participant


def _thread_summary(db: Session, thread: Thread, unread: int, acknowledged: bool) -> ThreadSummary:
    from sqlalchemy import func

    replies = db.scalar(select(func.count()).select_from(Post).where(Post.thread_id == thread.id))
    return ThreadSummary(
        id=thread.id,
        type=thread.type.value,
        title=thread.title,
        pinned=bool(thread.pinned and (not thread.pinned_until or thread.pinned_until > utcnow())),
        requires_ack=thread.requires_ack,
        acknowledged=acknowledged,
        status=thread.status.value,
        unread=unread,
        reply_count=max(0, (replies or 1) - 1),
        created_at=thread.created_at,
    )


def _submission_out(db: Session, participant: Participant) -> SubmissionOut | None:
    submission = submission_for_participant(db, participant)
    if submission is None:
        return None
    links = list(
        db.scalars(
            select(SubmissionLink)
            .where(SubmissionLink.submission_id == submission.id)
            .order_by(SubmissionLink.slot)
        )
    )
    return SubmissionOut(
        status=submission.status.value,
        locked=is_locked(db, submission),
        submitted_at=submission.submitted_at,
        slots=[
            SlotOut(
                slot=link.slot.value,
                drive_url=link.drive_url,
                access_status=link.access_status.value,
                filename=link.detected_filename,
                file_url=(
                    f"/files/{link.snapshot_key}?sig={sign_key(link.snapshot_key)}"
                    if link.snapshot_key
                    else None
                ),
            )
            for link in links
        ],
    )


def _require_submission_out(db: Session, participant: Participant) -> SubmissionOut:
    """After a mutation the submission is known to exist; this keeps that
    guarantee explicit rather than leaving an Optional to leak into the route."""
    out = _submission_out(db, participant)
    if out is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your submission is still being set up.")
    return out


@router.get("/dashboard", response_model=Dashboard)
def dashboard(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> Dashboard:
    participant = _participant(db, actor)
    programme = db.get(Programme, participant.programme_id)
    if programme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That programme no longer exists.")
    role = db.get(Role, programme.role_id)
    template = db.get(RoleTemplate, programme.role_id)
    from projet.models import Company

    company = db.get(Company, programme.company_id)

    submission = _submission_out(db, participant)
    # FR-506 — a fresh acceptance must never see a half-configured dashboard.
    provisioning = submission is None

    judging = None
    if participant.judging_session_id:
        row = db.get(JudgingSession, participant.judging_session_id)
        if row is not None:
            judging = JudgingSlot(
                starts_at=row.starts_at,
                location_or_meet_link=row.location_or_meet_link,
                run_order=participant.run_order,
            )

    counts = unread_counts(db, participant)
    from projet.models import ThreadRead

    acks = {
        row.thread_id: row.acknowledged_at is not None
        for row in db.scalars(select(ThreadRead).where(ThreadRead.participant_id == participant.id))
    }
    threads = [
        _thread_summary(db, thread, counts.get(thread.id, 0), acks.get(thread.id, False))
        for thread in visible_threads(db, participant)
    ]
    blocking = [
        _thread_summary(db, thread, counts.get(thread.id, 0), False)
        for thread in unacknowledged(db, participant)
    ]

    criteria = db.scalars(
        select(RubricCriterion)
        .where(RubricCriterion.programme_id == participant.programme_id)
        .order_by(RubricCriterion.slot)
    )
    # Excluded entries are not the participant's business: the company took
    # them out of the pack, so they are out of the pack.
    data_pack = released_resources(db, participant.programme_id)

    return Dashboard(
        provisioning=provisioning,
        programme=ProgrammeCard(
            id=programme.id,
            title=programme.title,
            company=company.name if company else "",
            role=role.name if role else "",
            status=programme.status.value,
            problem_statement=programme.problem_statement,
            deliverable=programme.deliverable_spec
            or (template.default_deliverable if template else ""),
            start_at=programme.start_at,
            submit_deadline_at=programme.submit_deadline_at,
            # FR-501/FR-1602 — stored UTC, rendered in their timezone.
            timezone=participant.person.timezone,
        ),
        submission=submission,
        judging=judging,
        criteria=[
            CriterionPublic(
                slot=c.slot,
                name=c.name,
                anchor_5=c.anchor_5,
                anchor_3=c.anchor_3,
                anchor_1=c.anchor_1,
            )
            for c in criteria
        ],
        data_pack=[
            DataPackEntry(
                label=r.label,
                url=resource_url(r.url_or_storage_key),
                provenance=r.provenance.value,
                licence=r.licence,
                confidential=r.confidential,
            )
            for r in data_pack
        ],
        threads=threads,
        blocking_acknowledgements=blocking,
    )


class LinkRequest(BaseModel):
    slot: str = Field(pattern="^(artifact|memo|extra)$")
    drive_url: str = Field(min_length=1, max_length=2000)


@router.put("/submission/link", response_model=SubmissionOut)
def put_link(
    payload: LinkRequest,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    """FR-802 — checked the moment it is pasted, with the answer inline."""
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your submission is still being set up.")
    try:
        set_link(db, submission, SubmissionSlot(payload.slot), payload.drive_url)
    except SubmissionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _require_submission_out(db, participant)


@router.put("/submission/upload", response_model=SubmissionOut)
async def upload_slot(
    slot: str = Form(pattern="^(artifact|memo|extra)$"),
    file: UploadFile = File(),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    """A slot filled by upload rather than a Drive link — a memo is one static
    document, not something worth keeping live and editable."""
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your submission is still being set up.")

    content = await file.read()
    if len(content) > MAX_SUBMISSION_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File must be under 20MB.")
    if file.content_type not in ALLOWED_SUBMISSION_UPLOAD_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File must be a PDF.")

    try:
        set_upload(
            db,
            submission,
            SubmissionSlot(slot),
            content=content,
            filename=file.filename or f"{slot}.pdf",
            mime_type=file.content_type,
        )
    except SubmissionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _require_submission_out(db, participant)


@router.delete("/submission/link/{slot}", response_model=SubmissionOut)
def delete_link(
    slot: str,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No submission yet.")
    try:
        clear_link(db, submission, SubmissionSlot(slot))
    except (SubmissionError, ValueError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _require_submission_out(db, participant)


@router.post("/submission/recheck", response_model=SubmissionOut)
def recheck_links(
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> SubmissionOut:
    """ "I've fixed the sharing setting" — check again without re-pasting."""
    participant = _participant(db, actor)
    submission = submission_for_participant(db, participant)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No submission yet.")
    recheck(db, submission)
    db.commit()
    return _require_submission_out(db, participant)


@router.post("/threads/{thread_id}/read", status_code=204)
def read_thread(
    thread_id: uuid.UUID,
    acknowledge: bool = False,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_participant),
) -> None:
    participant = _participant(db, actor)
    thread = db.get(Thread, thread_id)
    if thread is None or thread.programme_id != participant.programme_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    mark_read(db, thread, participant, acknowledge=acknowledge)
    db.commit()
