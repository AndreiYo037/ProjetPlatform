"""Channel threads and posts (FR-600 to FR-614).

One set of endpoints for all three actor types, with who-may-do-what decided
here rather than by three parallel route trees.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.api.deps import get_programme_or_404, require_actor
from projet.db import get_session
from projet.models import (
    Attachment,
    Participant,
    Post,
    Programme,
    Thread,
    ThreadMember,
)
from projet.models.base import utcnow
from projet.models.enums import AuthorRole, ThreadType
from projet.services.auth import Actor
from projet.services.messaging import (
    MessagingError,
    open_thread,
    reply,
    share_to_channel,
    similar_threads,
    unanswered_threads,
)
from projet.storage import get_storage, sign_key

router = APIRouter(tags=["threads"])

MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}


class AttachmentOut(BaseModel):
    filename: str
    url: str
    size_bytes: int | None
    mime_type: str | None


class PostOut(BaseModel):
    id: uuid.UUID
    body: str
    author_role: str
    author_label: str
    created_at: datetime
    edited_at: datetime | None
    removed: bool
    attachments: list[AttachmentOut]


class ThreadOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str | None
    author_role: str
    is_anonymous: bool
    pinned: bool
    requires_ack: bool
    status: str
    created_at: datetime
    posts: list[PostOut]


class ThreadCreate(BaseModel):
    type: str = Field(
        pattern="^(announcement|resource|question_challenge|question_logistics|direct)$"
    )
    title: str = Field(min_length=1, max_length=400)
    body: str = Field(min_length=1)
    is_anonymous: bool = False
    requires_ack: bool = False


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1)


class ThreadCreated(BaseModel):
    thread: ThreadOut
    warning: str | None = None


def _actor_role(actor: Actor) -> AuthorRole:
    if actor.is_platform:
        return AuthorRole.ADMIN
    if actor.is_company_user:
        return AuthorRole.REP
    return AuthorRole.PARTICIPANT


def _participant_for(db: Session, actor: Actor, programme_id: uuid.UUID) -> Participant | None:
    return db.scalar(
        select(Participant)
        .where(Participant.person_id == actor.id)
        .where(Participant.programme_id == programme_id)
    )


def _may_see_programme_channel(db: Session, actor: Actor, programme: Programme) -> bool:
    """Participants reach the channel through their participation; company
    users and admin through programme scoping (FR-015)."""
    if actor.is_participant:
        return _participant_for(db, actor, programme.id) is not None
    from projet.api.deps import can_see_programme

    return can_see_programme(db, actor, programme)


def _programme_for_actor(
    programme_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> Programme:
    programme = db.get(Programme, programme_id)
    if programme is None or not _may_see_programme_channel(db, actor, programme):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programme not found.")
    return programme


def _may_see_thread(db: Session, actor: Actor, thread: Thread) -> bool:
    if thread.type != ThreadType.DIRECT:
        return True
    if actor.is_platform:
        # FR-606 — admin can see all direct threads, stated in participant terms.
        return True
    member = db.get(ThreadMember, (thread.id, actor.id))
    return member is not None


def _author_label(thread: Thread, post: Post) -> str:
    if post.author_role == AuthorRole.PARTICIPANT and thread.is_anonymous:
        return "A participant"
    return {
        AuthorRole.ADMIN: "Projet",
        AuthorRole.REP: "The company",
        AuthorRole.PARTICIPANT: "A participant",
    }[post.author_role]


def _thread_out(db: Session, thread: Thread) -> ThreadOut:
    posts = list(
        db.scalars(select(Post).where(Post.thread_id == thread.id).order_by(Post.created_at))
    )
    out_posts = []
    for post in posts:
        attachments = db.scalars(select(Attachment).where(Attachment.post_id == post.id))
        out_posts.append(
            PostOut(
                id=post.id,
                # FR-613 — a removal leaves a visible tombstone, not a gap.
                body="[removed]" if post.removed_at else post.body,
                author_role=post.author_role.value,
                author_label=_author_label(thread, post),
                created_at=post.created_at,
                edited_at=post.edited_at,
                removed=post.removed_at is not None,
                attachments=[
                    AttachmentOut(
                        filename=a.filename,
                        url=f"/files/{a.storage_key}?sig={sign_key(a.storage_key)}",
                        size_bytes=a.size_bytes,
                        mime_type=a.mime_type,
                    )
                    for a in attachments
                ],
            )
        )
    return ThreadOut(
        id=thread.id,
        type=thread.type.value,
        title=thread.title,
        author_role=thread.author_role.value,
        is_anonymous=thread.is_anonymous,
        pinned=bool(thread.pinned and (not thread.pinned_until or thread.pinned_until > utcnow())),
        requires_ack=thread.requires_ack,
        status=thread.status.value,
        created_at=thread.created_at,
        posts=out_posts,
    )


@router.get("/programmes/{programme_id}/threads", response_model=list[ThreadOut])
def list_threads(
    programme: Programme = Depends(_programme_for_actor),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> list[ThreadOut]:
    threads = db.scalars(
        select(Thread)
        .where(Thread.programme_id == programme.id)
        .where(Thread.merged_into_id.is_(None))
        .order_by(Thread.pinned.desc(), Thread.created_at.desc())
    )
    return [_thread_out(db, t) for t in threads if _may_see_thread(db, actor, t)]


@router.get("/programmes/{programme_id}/threads/similar", response_model=list[dict])
def find_similar(
    title: str = Query(min_length=1, max_length=400),
    programme: Programme = Depends(_programme_for_actor),
    db: Session = Depends(get_session),
) -> list[dict]:
    """FR-611b — surfaced inline as a participant types, before they post."""
    return [
        {"id": str(t.id), "title": t.title, "status": t.status.value}
        for t in similar_threads(db, programme.id, title)
    ]


@router.post("/programmes/{programme_id}/threads", response_model=ThreadCreated, status_code=201)
def create_thread(
    payload: ThreadCreate,
    programme: Programme = Depends(_programme_for_actor),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> ThreadCreated:
    role = _actor_role(actor)
    members: list[tuple[uuid.UUID, AuthorRole]] | None = None
    if payload.type == ThreadType.DIRECT.value and actor.is_participant:
        # A participant's direct thread reaches the rep and admin; who answers
        # is their business (FR-605).
        members = []
    try:
        thread, warning = open_thread(
            db,
            programme,
            thread_type=ThreadType(payload.type),
            title=payload.title,
            body=payload.body,
            author_id=actor.id,
            author_role=role,
            is_anonymous=payload.is_anonymous and role == AuthorRole.PARTICIPANT,
            requires_ack=payload.requires_ack and role != AuthorRole.PARTICIPANT,
            member_ids=members,
        )
    except MessagingError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    db.commit()
    return ThreadCreated(
        thread=_thread_out(db, thread),
        warning=warning.message if warning else None,
    )


def _thread_or_404(db: Session, actor: Actor, thread_id: uuid.UUID) -> Thread:
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    programme = db.get(Programme, thread.programme_id)
    if programme is None or not _may_see_programme_channel(db, actor, programme):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    if not _may_see_thread(db, actor, thread):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found.")
    return thread


@router.get("/threads/{thread_id}", response_model=ThreadOut)
def get_thread(
    thread_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> ThreadOut:
    return _thread_out(db, _thread_or_404(db, actor, thread_id))


@router.post("/threads/{thread_id}/posts", response_model=ThreadOut, status_code=201)
def post_reply(
    thread_id: uuid.UUID,
    payload: ReplyCreate,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> ThreadOut:
    thread = _thread_or_404(db, actor, thread_id)
    reply(db, thread, body=payload.body, author_id=actor.id, author_role=_actor_role(actor))
    db.commit()
    return _thread_out(db, thread)


@router.post("/threads/{thread_id}/attachments", response_model=ThreadOut, status_code=201)
async def add_attachment(
    thread_id: uuid.UUID,
    file: UploadFile = File(),
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> ThreadOut:
    """FR-608/609 — served from platform storage, scoped to the programme."""
    thread = _thread_or_404(db, actor, thread_id)
    content = await file.read()
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "That file is over 100MB. Share it as a link instead.",
        )
    if file.content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{file.content_type} is not an accepted file type.",
        )

    post = Post(
        thread_id=thread.id,
        author_id=actor.id,
        author_role=_actor_role(actor),
        body=f"Attached {file.filename}",
    )
    db.add(post)
    db.flush()

    key = f"attachments/{thread.programme_id}/{post.id}/{file.filename}"
    get_storage().put(key, content, file.content_type)
    db.add(
        Attachment(
            post_id=post.id,
            filename=file.filename or "attachment",
            storage_key=key,
            mime_type=file.content_type,
            size_bytes=len(content),
        )
    )
    db.commit()
    return _thread_out(db, thread)


@router.post("/threads/{thread_id}/share", response_model=ThreadOut, status_code=201)
def share(
    thread_id: uuid.UUID,
    anonymise: bool = True,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> ThreadOut:
    """FR-607 — the rep decides what is general and what is personal."""
    if actor.is_participant:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the company or admin can share.")
    thread = _thread_or_404(db, actor, thread_id)
    try:
        shared = share_to_channel(
            db, thread, author_id=actor.id, author_role=_actor_role(actor), anonymise=anonymise
        )
    except MessagingError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    db.commit()
    return _thread_out(db, shared)


@router.delete("/posts/{post_id}", status_code=204)
def remove_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_session),
    actor: Actor = Depends(require_actor),
) -> None:
    """FR-613 — admin can remove any post; removals leave a tombstone."""
    if not actor.is_platform:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required.")
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found.")
    post.removed_at = utcnow()
    db.commit()


class DigestThread(BaseModel):
    id: uuid.UUID
    title: str | None
    type: str
    created_at: datetime
    age_hours: float


@router.get("/programmes/{programme_id}/digest", response_model=list[DigestThread])
def rep_digest(
    programme: Programme = Depends(get_programme_or_404),
    db: Session = Depends(get_session),
) -> list[DigestThread]:
    """FR-612 — unanswered threads, reachable in one click from an email."""
    now = utcnow()
    return [
        DigestThread(
            id=t.id,
            title=t.title,
            type=t.type.value,
            created_at=t.created_at,
            age_hours=round((now - t.created_at).total_seconds() / 3600, 1),
        )
        for t in unanswered_threads(db, programme.id)
    ]
