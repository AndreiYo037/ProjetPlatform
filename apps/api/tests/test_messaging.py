"""The programme channel (FR-600).

Two rules carry real weight here: a dataset drop mid-programme has to reach
everyone at the same moment, and someone else's direct thread is not yours to
read.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from projet.models import Post
from projet.models.base import utcnow
from projet.models.enums import AuthorRole, ThreadStatus, ThreadType
from projet.services.messaging import (
    MessagingError,
    mark_read,
    open_thread,
    reply,
    share_to_channel,
    similar_threads,
    unacknowledged,
    unanswered_threads,
    unread_counts,
    visible_threads,
)


def _ask(session, programme, participant, title="How is revenue defined?", body="Net or gross?"):
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.QUESTION_CHALLENGE,
        title=title,
        body=body,
        author_id=participant.person_id,
        author_role=AuthorRole.PARTICIPANT,
    )
    return thread


def test_a_participant_can_ask_and_a_rep_answers_directly(
    session, programme, participant_factory, rep
):
    """FR-611 — no admin triage step; nothing waits on admin."""
    participant = participant_factory()
    thread = _ask(session, programme, participant)
    assert thread.status == ThreadStatus.OPEN

    reply(session, thread, body="Net.", author_id=rep.id, author_role=AuthorRole.REP)
    assert thread.status == ThreadStatus.ANSWERED


def test_a_participant_reply_does_not_mark_their_own_question_answered(
    session, programme, participant_factory
):
    participant = participant_factory()
    thread = _ask(session, programme, participant)
    reply(
        session,
        thread,
        body="To be clear, I mean FY24.",
        author_id=participant.person_id,
        author_role=AuthorRole.PARTICIPANT,
    )
    assert thread.status == ThreadStatus.OPEN


def test_participants_cannot_post_announcements(session, programme, participant_factory):
    participant = participant_factory()
    with pytest.raises(MessagingError, match="Only the company or admin"):
        open_thread(
            session,
            programme,
            thread_type=ThreadType.ANNOUNCEMENT,
            title="Everyone read this",
            body="...",
            author_id=participant.person_id,
            author_role=AuthorRole.PARTICIPANT,
        )


def test_a_resource_drop_before_kickoff_is_an_ordinary_post(session, programme, rep):
    programme.start_at = utcnow() + timedelta(days=2)
    session.flush()
    thread, warning = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Starter dataset",
        body="Here it is.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )
    assert not thread.pinned
    assert warning is None


def test_a_resource_drop_after_kickoff_is_pinned_and_needs_acknowledgement(session, programme, rep):
    """FR-610 — fairness depends on everyone receiving it at the same moment."""
    programme.start_at = utcnow() - timedelta(days=1)
    programme.submit_deadline_at = utcnow() + timedelta(days=5)
    session.flush()

    thread, warning = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Extra dataset",
        body="Just got sign-off on this.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )

    assert thread.pinned
    assert thread.requires_ack
    assert thread.pinned_until > utcnow()
    assert warning is not None and not warning.late


def test_a_late_drop_warns_the_poster_about_the_deadline(session, programme, rep):
    """The warning goes to the person who can act on it, rather than being
    logged somewhere nobody reads."""
    programme.start_at = utcnow() - timedelta(days=4)
    programme.submit_deadline_at = utcnow() + timedelta(hours=20)
    session.flush()

    _, warning = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Late dataset",
        body="Sorry this is late.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )

    assert warning is not None and warning.late
    assert "extending the deadline" in (warning.message or "")


def test_an_unacknowledged_drop_blocks_until_acknowledged(
    session, programme, participant_factory, rep
):
    """FR-703 — renders as a blocking banner."""
    programme.start_at = utcnow() - timedelta(days=1)
    session.flush()
    participant = participant_factory()
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Dataset",
        body="Here.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )

    assert [t.id for t in unacknowledged(session, participant)] == [thread.id]

    mark_read(session, thread, participant, acknowledge=True)
    assert unacknowledged(session, participant) == []


def test_reading_without_acknowledging_does_not_clear_the_block(
    session, programme, participant_factory, rep
):
    programme.start_at = utcnow() - timedelta(days=1)
    session.flush()
    participant = participant_factory()
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.RESOURCE,
        title="Dataset",
        body="Here.",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )
    mark_read(session, thread, participant, acknowledge=False)

    assert [t.id for t in unacknowledged(session, participant)] == [thread.id]


def test_someone_elses_direct_thread_is_not_visible(session, programme, participant_factory, rep):
    """FR-605 — excluded by the query, not hidden in the UI."""
    mine = participant_factory(name="Mine")
    theirs = participant_factory(name="Theirs")

    my_thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.DIRECT,
        title="A personal circumstance",
        body="I have an exam on day 5.",
        author_id=mine.person_id,
        author_role=AuthorRole.PARTICIPANT,
    )
    their_thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.DIRECT,
        title="Something else",
        body="Private.",
        author_id=theirs.person_id,
        author_role=AuthorRole.PARTICIPANT,
    )

    visible_to_mine = {t.id for t in visible_threads(session, mine)}
    assert my_thread.id in visible_to_mine
    assert their_thread.id not in visible_to_mine


def test_sharing_a_direct_answer_to_the_channel_anonymises_by_default(
    session, programme, participant_factory, rep
):
    """FR-607 — the mechanism for 'the whole cohort should know this'."""
    participant = participant_factory()
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.DIRECT,
        title="Is the 2023 report in scope?",
        body="Is the 2023 report in scope?",
        author_id=participant.person_id,
        author_role=AuthorRole.PARTICIPANT,
    )
    reply(session, thread, body="Yes, and 2022.", author_id=rep.id, author_role=AuthorRole.REP)

    shared = share_to_channel(session, thread, author_id=rep.id, author_role=AuthorRole.REP)

    assert shared.type == ThreadType.QUESTION_CHALLENGE
    assert shared.is_anonymous
    body = session.scalars(select_posts(shared.id)).first().body
    assert "Someone asked" in body
    assert "Yes, and 2022." in body


def select_posts(thread_id):
    from sqlalchemy import select

    return select(Post).where(Post.thread_id == thread_id).order_by(Post.created_at)


def test_a_channel_thread_cannot_be_shared(session, programme, rep):
    thread, _ = open_thread(
        session,
        programme,
        thread_type=ThreadType.ANNOUNCEMENT,
        title="Already public",
        body="...",
        author_id=rep.id,
        author_role=AuthorRole.REP,
    )
    with pytest.raises(MessagingError, match="Only a direct thread"):
        share_to_channel(session, thread, author_id=rep.id, author_role=AuthorRole.REP)


def test_duplicate_detection_surfaces_a_similar_question(session, programme, participant_factory):
    """FR-611b — does more for readability than merging afterwards."""
    participant = participant_factory()
    _ask(session, programme, participant, title="How is revenue defined in the dataset?")

    matches = similar_threads(session, programme.id, "How should revenue be defined?")
    assert matches, "a near-identical question should surface"

    assert similar_threads(session, programme.id, "Where do I submit my deck?") == []


def test_unread_counts_track_new_posts(session, programme, participant_factory, rep):
    participant = participant_factory()
    thread = _ask(session, programme, participant)

    assert unread_counts(session, participant)[thread.id] == 1

    mark_read(session, thread, participant)
    assert unread_counts(session, participant)[thread.id] == 0

    reply(session, thread, body="Net.", author_id=rep.id, author_role=AuthorRole.REP)
    assert unread_counts(session, participant)[thread.id] == 1


def test_the_rep_digest_lists_only_what_is_waiting(session, programme, participant_factory, rep):
    """FR-612 — one email, one click per item."""
    participant = participant_factory()
    open_question = _ask(session, programme, participant, title="Unanswered one")
    answered = _ask(session, programme, participant, title="Answered one")
    reply(session, answered, body="Done.", author_id=rep.id, author_role=AuthorRole.REP)

    waiting = [t.id for t in unanswered_threads(session, programme.id)]
    assert open_question.id in waiting
    assert answered.id not in waiting
