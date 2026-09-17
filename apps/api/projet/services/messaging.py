"""The programme channel (FR-600).

Two design decisions from the PRD shape this module:

  * No admin triage step (FR-611). Participants post directly and the rep
    answers directly. Admin has full visibility and can step in, but nothing
    waits on them.
  * A dataset drop after start_at is an event, not just a post (FR-610).
    Fairness depends on everyone receiving it at the same moment, so the
    platform pins it, requires acknowledgement, and warns admin if it lands
    close to the deadline.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from projet.models import (
    Participant,
    Post,
    Programme,
    Thread,
    ThreadMember,
    ThreadRead,
)
from projet.models.base import utcnow
from projet.models.enums import AuthorRole, ThreadStatus, ThreadType

PIN_DURATION = timedelta(hours=24)
# FR-610 — a drop this close to the deadline may warrant extending it.
LATE_DROP_WINDOW = timedelta(hours=48)

PARTICIPANT_THREAD_TYPES = (ThreadType.QUESTION_CHALLENGE, ThreadType.QUESTION_LOGISTICS)
BROADCAST_TYPES = (ThreadType.ANNOUNCEMENT, ThreadType.RESOURCE)

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
    ]
)


class MessagingError(RuntimeError):
    pass


@dataclass
class DropWarning:
    """Returned to the poster, not swallowed: they are the one who can act."""

    late: bool
    hours_to_deadline: float | None
    message: str | None


def _keywords(text: str) -> set[str]:
    return {
        word for word in _WORD.findall(text.lower()) if word not in _STOPWORDS and len(word) > 2
    }


def similar_threads(
    session: Session, programme_id: uuid.UUID, title: str, limit: int = 3
) -> list[Thread]:
    """FR-611b — duplicate detection at post time.

    Surfacing similar threads as someone types does more to keep the channel
    readable than merging duplicates afterwards ever did. Deliberately a simple
    keyword overlap: it runs on every keystroke and a cohort's channel is
    small, so cleverness here would cost more than it returns.
    """
    words = _keywords(title)
    if not words:
        return []

    candidates = session.scalars(
        select(Thread)
        .where(Thread.programme_id == programme_id)
        .where(Thread.type.in_(PARTICIPANT_THREAD_TYPES))
        .where(Thread.merged_into_id.is_(None))
        .order_by(Thread.created_at.desc())
        .limit(100)
    )

    scored: list[tuple[float, Thread]] = []
    for thread in candidates:
        other = _keywords(thread.title or "")
        if not other:
            continue
        overlap = len(words & other) / len(words | other)
        if overlap >= 0.3:
            scored.append((overlap, thread))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [thread for _, thread in scored[:limit]]


def open_thread(
    session: Session,
    programme: Programme,
    *,
    thread_type: ThreadType,
    title: str,
    body: str,
    author_id: uuid.UUID | None,
    author_role: AuthorRole,
    is_anonymous: bool = False,
    requires_ack: bool = False,
    member_ids: list[tuple[uuid.UUID, AuthorRole]] | None = None,
) -> tuple[Thread, DropWarning | None]:
    """Open a thread and post its first message."""
    if author_role == AuthorRole.PARTICIPANT and thread_type in BROADCAST_TYPES:
        raise MessagingError("Only the company or admin can post announcements and resources.")

    thread = Thread(
        programme_id=programme.id,
        type=thread_type,
        title=title.strip()[:400],
        author_id=author_id,
        author_role=author_role,
        is_anonymous=is_anonymous,
        requires_ack=requires_ack,
    )

    warning = None
    if thread_type == ThreadType.RESOURCE:
        warning = _apply_drop_rules(programme, thread)

    session.add(thread)
    session.flush()

    if thread_type == ThreadType.DIRECT:
        for member_id, member_role in member_ids or []:
            session.add(ThreadMember(thread_id=thread.id, user_id=member_id, user_role=member_role))
        if author_id is not None:
            session.add(ThreadMember(thread_id=thread.id, user_id=author_id, user_role=author_role))

    session.add(Post(thread_id=thread.id, author_id=author_id, author_role=author_role, body=body))
    session.flush()
    return thread, warning


def _apply_drop_rules(programme: Programme, thread: Thread) -> DropWarning | None:
    """FR-610 — a dataset drop after start_at is an event, not just a post."""
    now = utcnow()
    started = programme.start_at is not None and now >= programme.start_at
    if not started:
        return None

    thread.pinned = True
    thread.pinned_until = now + PIN_DURATION
    thread.requires_ack = True

    if programme.submit_deadline_at is None:
        return DropWarning(late=False, hours_to_deadline=None, message=None)

    remaining = programme.submit_deadline_at - now
    hours = round(remaining.total_seconds() / 3600, 1)
    if remaining <= LATE_DROP_WINDOW:
        return DropWarning(
            late=True,
            hours_to_deadline=hours,
            message=(
                f"This lands {hours:g} hours before the deadline. Everyone receives it at "
                "the same moment, but that may not be enough time to use it — consider "
                "extending the deadline."
            ),
        )
    return DropWarning(late=False, hours_to_deadline=hours, message=None)


def reply(
    session: Session,
    thread: Thread,
    *,
    body: str,
    author_id: uuid.UUID | None,
    author_role: AuthorRole,
) -> Post:
    """FR-604 — anyone in the programme can reply to any thread."""
    post = Post(thread_id=thread.id, author_id=author_id, author_role=author_role, body=body)
    session.add(post)
    # A rep or admin answering marks the thread answered; a participant adding
    # to their own question does not.
    if (
        author_role in (AuthorRole.REP, AuthorRole.ADMIN)
        and thread.type in PARTICIPANT_THREAD_TYPES
    ):
        thread.status = ThreadStatus.ANSWERED
    session.flush()
    return post


def standing_announcement_thread(
    session: Session,
    programme: Programme,
    *,
    author_id: uuid.UUID | None,
    author_role: AuthorRole,
) -> Thread:
    """The announcements channel's one continuous thread.

    Marked by having no subject, which is also what it means: a company
    sharing a link, then a correction, then a reminder is having one
    conversation, and asking it to name each turn is asking it to name things
    that do not need names.
    """
    thread = session.scalar(
        select(Thread)
        .where(Thread.programme_id == programme.id)
        .where(Thread.type == ThreadType.ANNOUNCEMENT)
        .where(Thread.title.is_(None))
        .where(Thread.merged_into_id.is_(None))
        .order_by(Thread.created_at)
    )
    if thread is None:
        thread = Thread(
            programme_id=programme.id,
            type=ThreadType.ANNOUNCEMENT,
            title=None,
            author_id=author_id,
            author_role=author_role,
        )
        session.add(thread)
        session.flush()
    return thread


def post_announcement(
    session: Session,
    programme: Programme,
    *,
    body: str,
    author_id: uuid.UUID | None,
    author_role: AuthorRole,
    requires_ack: bool = False,
) -> tuple[Thread, Post]:
    """Share something with the whole cohort.

    One that must be acknowledged is the exception to the continuous thread:
    FR-703 blocks every dashboard until each participant confirms, and that is
    per-message, so it gets a thread of its own. Its title is taken from the
    message rather than asked for — the participant sees it on the blocking
    banner, which is the only place a subject was ever needed.
    """
    if author_role == AuthorRole.PARTICIPANT:
        raise MessagingError("Only the company or admin can post announcements.")

    if requires_ack:
        thread = Thread(
            programme_id=programme.id,
            type=ThreadType.ANNOUNCEMENT,
            title=_first_line(body),
            author_id=author_id,
            author_role=author_role,
            requires_ack=True,
        )
        session.add(thread)
        session.flush()
    else:
        thread = standing_announcement_thread(
            session, programme, author_id=author_id, author_role=author_role
        )

    post = Post(thread_id=thread.id, author_id=author_id, author_role=author_role, body=body)
    session.add(post)
    session.flush()
    return thread, post


def _first_line(body: str, limit: int = 120) -> str:
    """A label for the blocking banner, not a subject the company typed."""
    line = next((part.strip() for part in body.splitlines() if part.strip()), "Announcement")
    return line if len(line) <= limit else f"{line[: limit - 1].rstrip()}…"


def share_to_channel(
    session: Session,
    thread: Thread,
    *,
    author_id: uuid.UUID | None,
    author_role: AuthorRole,
    anonymise: bool = True,
) -> Thread:
    """FR-607 — copy a direct exchange into the channel when the whole cohort
    should know.

    The rep decides what is general and what is personal; this is the mechanism
    for that, not a restriction on it. Anonymised by default because the
    question was asked privately.
    """
    if thread.type != ThreadType.DIRECT:
        raise MessagingError("Only a direct thread can be shared to the channel.")

    posts = list(
        session.scalars(select(Post).where(Post.thread_id == thread.id).order_by(Post.created_at))
    )
    if not posts:
        raise MessagingError("There is nothing in that thread to share.")

    body = "\n\n".join(
        f"**{'Someone asked' if anonymise else post.author_role.value}:** {post.body}"
        if post.author_role == AuthorRole.PARTICIPANT
        else f"**Answer:** {post.body}"
        for post in posts
    )
    shared = Thread(
        programme_id=thread.programme_id,
        type=ThreadType.QUESTION_CHALLENGE,
        title=thread.title or "From a direct question",
        author_id=author_id,
        author_role=author_role,
        is_anonymous=anonymise,
        status=ThreadStatus.ANSWERED,
    )
    session.add(shared)
    session.flush()
    session.add(Post(thread_id=shared.id, author_id=author_id, author_role=author_role, body=body))
    session.flush()
    return shared


def mark_read(
    session: Session, thread: Thread, participant: Participant, *, acknowledge: bool = False
) -> ThreadRead:
    row = session.get(ThreadRead, (thread.id, participant.id))
    if row is None:
        row = ThreadRead(thread_id=thread.id, participant_id=participant.id)
        session.add(row)
    row.read_at = utcnow()
    if acknowledge and thread.requires_ack:
        row.acknowledged_at = utcnow()
    session.flush()
    return row


def unacknowledged(session: Session, participant: Participant) -> list[Thread]:
    """FR-703 — these render as a blocking banner until acknowledged."""
    acknowledged = select(ThreadRead.thread_id).where(
        ThreadRead.participant_id == participant.id,
        ThreadRead.acknowledged_at.is_not(None),
    )
    return list(
        session.scalars(
            select(Thread)
            .where(Thread.programme_id == participant.programme_id)
            .where(Thread.requires_ack.is_(True))
            .where(Thread.id.not_in(acknowledged))
            .order_by(Thread.created_at.desc())
        )
    )


def unread_counts(session: Session, participant: Participant) -> dict[uuid.UUID, int]:
    """FR-614 — unread posts per thread for this participant."""
    reads = {
        row.thread_id: row.read_at
        for row in session.scalars(
            select(ThreadRead).where(ThreadRead.participant_id == participant.id)
        )
    }
    counts: dict[uuid.UUID, int] = {}
    for thread in visible_threads(session, participant):
        read_at = reads.get(thread.id)
        statement = select(func.count()).select_from(Post).where(Post.thread_id == thread.id)
        if read_at is not None:
            statement = statement.where(Post.created_at > read_at)
        counts[thread.id] = session.scalar(statement) or 0
    return counts


def visible_threads(session: Session, participant: Participant) -> list[Thread]:
    """The channel, plus this participant's own direct threads.

    Someone else's direct thread is not theirs to read, so it is excluded by
    the query rather than hidden in the UI.
    """
    # ThreadMember.user_id holds the *person* id, because that is what an Actor
    # carries and what every author_id in this module is. ThreadRead is keyed on
    # the participant instead, since read state belongs to one cohort. Mixing
    # the two silently hides a participant's own direct threads from them.
    direct_ids = select(ThreadMember.thread_id).where(ThreadMember.user_id == participant.person_id)
    return list(
        session.scalars(
            select(Thread)
            .where(Thread.programme_id == participant.programme_id)
            .where(Thread.merged_into_id.is_(None))
            .where(
                or_(
                    Thread.type != ThreadType.DIRECT,
                    Thread.id.in_(direct_ids),
                )
            )
            .order_by(Thread.pinned.desc(), Thread.created_at.desc())
        )
    )


def unanswered_threads(session: Session, programme_id: uuid.UUID) -> list[Thread]:
    """FR-612 — the rep digest view: what is waiting on them."""
    return list(
        session.scalars(
            select(Thread)
            .where(Thread.programme_id == programme_id)
            .where(Thread.status == ThreadStatus.OPEN)
            .where(
                Thread.type.in_(
                    [
                        ThreadType.QUESTION_CHALLENGE,
                        ThreadType.QUESTION_LOGISTICS,
                        ThreadType.DIRECT,
                    ]
                )
            )
            .order_by(Thread.created_at)
        )
    )
