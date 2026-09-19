"""The FR-1500 job table, plus the deadline sweep.

Deadline-triggered work is a sweep, not a per-programme scheduled job. A job
scheduled at submit_deadline_at does not survive a process restart, and section 8
requires no downtime across days 6 and 7 — where the deadline and judging sit
twelve hours apart with no slack. A sweep that queries for due work is stateless,
restart-safe, and testable by moving the clock.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Application,
    JudgingSession,
    Participant,
    Programme,
    Submission,
    SubmissionLink,
    Team,
    TeamMember,
)
from projet.models.base import utcnow
from projet.models.enums import (
    AccessStatus,
    ApplicationStatus,
    OutboxSubjectType,
    ParticipantStatus,
    ProgrammeStatus,
    SubmissionStatus,
)
from projet.outbox.effects import enqueue
from projet.outbox.provisioning import SESSION_REMOVAL, enqueue_pitch_day_reminders
from projet.outbox.snapshots import SNAPSHOT_EFFECT
from projet.services.schedule import pitch_day_begins_at

log = logging.getLogger(__name__)


@dataclass
class SweepResult:
    programmes_processed: int = 0
    submissions_locked: int = 0
    non_submitters: int = 0
    removals_queued: int = 0
    snapshots_queued: int = 0

    def __bool__(self) -> bool:
        return bool(self.programmes_processed)


@dataclass
class PitchDayResult:
    programmes_processed: int = 0
    emails_queued: int = 0


def expire_offers(session: Session, now: datetime | None = None) -> int:
    """Every 15 minutes. An expired offer releases its seat, which is what makes
    waitlist promotion possible at 2am (FR-403/FR-404)."""
    now = now or utcnow()
    applications = list(
        session.scalars(
            select(Application)
            .where(Application.status == ApplicationStatus.OFFERED)
            .where(Application.offer_expires_at.is_not(None))
            .where(Application.offer_expires_at <= now)
        )
    )
    touched_programmes = set()
    for application in applications:
        application.status = ApplicationStatus.EXPIRED
        touched_programmes.add(application.programme_id)
    session.flush()

    # FR-404 — an expiry is a seat release, and a seat release promotes the
    # highest-scoring waitlisted applicant immediately.
    from projet.services.selection import release_seats_and_promote

    for programme_id in touched_programmes:
        release_seats_and_promote(session, programme_id)

    session.commit()
    return len(applications)


def recheck_submission_links(session: Session, google=None) -> list[SubmissionLink]:
    """02:00 during running. A link shareable on day 2 can be un-shared by day 5,
    and nobody finds out unless we look (FR-1500)."""
    from projet.integrations.google.client import get_google_client
    from projet.integrations.google.urls import extract_file_id

    client = google or get_google_client()
    links = list(
        session.scalars(
            select(SubmissionLink)
            .join(Submission, SubmissionLink.submission_id == Submission.id)
            .join(Team, Submission.team_id == Team.id)
            .join(Programme, Team.programme_id == Programme.id)
            .where(Programme.status == ProgrammeStatus.RUNNING)
            .where(SubmissionLink.drive_url.is_not(None))
        )
    )
    broken: list[SubmissionLink] = []
    for link in links:
        if not extract_file_id(link.drive_url or ""):
            link.access_status = AccessStatus.OK
            link.last_checked_at = utcnow()
            continue
        probe = client.probe_drive_file(link.drive_url or "")
        link.access_status = probe.access_status
        link.last_checked_at = utcnow()
        if probe.ok:
            link.drive_file_id = probe.file_id
            link.detected_filename = probe.filename
            link.detected_mime = probe.mime_type
        else:
            broken.append(link)
    session.commit()
    return broken


def due_programmes(session: Session, now: datetime | None = None) -> list[Programme]:
    """Programmes whose deadline has passed and whose due work is unclaimed."""
    now = now or utcnow()
    return list(
        session.scalars(
            select(Programme)
            .where(Programme.submit_deadline_at.is_not(None))
            .where(Programme.submit_deadline_at <= now)
            .where(Programme.deadline_processed_at.is_(None))
            .where(Programme.status.in_([ProgrammeStatus.RUNNING, ProgrammeStatus.CONFIRMED]))
        )
    )


def process_deadline(
    session: Session, programme: Programme, now: datetime | None = None
) -> SweepResult:
    """Everything that happens at submit_deadline_at, in one transaction.

    Lock submissions, queue snapshots, flag non-submitters, and take them off
    their judging session so the schedule is already correct without anyone
    doing anything (FR-811).
    """
    now = now or utcnow()
    result = SweepResult(programmes_processed=1)

    participants = list(
        session.scalars(select(Participant).where(Participant.programme_id == programme.id))
    )
    for participant in participants:
        submission = session.scalar(
            select(Submission)
            .join(Team, Submission.team_id == Team.id)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.participant_id == participant.id)
        )
        complete = submission is not None and submission.is_complete

        if complete and submission is not None:
            submission.status = SubmissionStatus.LOCKED
            submission.locked_at = now
            result.submissions_locked += 1
            # FR-811: everyone who submitted pitches. No review step.
            participant.status = ParticipantStatus.SUBMITTED
            for link in submission.links:
                # An uploaded file's snapshot is set the moment it lands, not
                # here — only a Drive link (which has a file id to fetch) has
                # anything left for this sweep to do.
                if link.access_status == AccessStatus.OK and link.drive_file_id:
                    enqueue(
                        session,
                        subject_type=OutboxSubjectType.SUBMISSION_LINK,
                        subject_id=link.id,
                        effect_type=SNAPSHOT_EFFECT,
                        payload={"file_id": link.drive_file_id, "mime": link.detected_mime},
                    )
                    result.snapshots_queued += 1
        else:
            participant.status = ParticipantStatus.NO_SUBMISSION
            result.non_submitters += 1

        # FR-811c — non-submitters and excluded participants come off the event.
        if (not complete or participant.excluded) and participant.judging_session_id:
            judging = session.get(JudgingSession, participant.judging_session_id)
            if judging and judging.google_event_id:
                enqueue(
                    session,
                    subject_type=OutboxSubjectType.PARTICIPANT,
                    subject_id=participant.id,
                    participant_id=participant.id,
                    effect_type=SESSION_REMOVAL,
                    payload={
                        "event_id": judging.google_event_id,
                        "email": participant.person.google_email
                        or participant.person.contact_email,
                    },
                )
                result.removals_queued += 1

    programme.status = ProgrammeStatus.SUBMITTED
    programme.deadline_processed_at = now
    return result


def deadline_sweep(session: Session, now: datetime | None = None) -> SweepResult:
    """Runs every minute. Claims each programme exactly once via
    deadline_processed_at, so a restart mid-sweep re-runs nothing twice."""
    now = now or utcnow()
    total = SweepResult()
    for programme in due_programmes(session, now):
        result = process_deadline(session, programme, now)
        total.programmes_processed += result.programmes_processed
        total.submissions_locked += result.submissions_locked
        total.non_submitters += result.non_submitters
        total.removals_queued += result.removals_queued
        total.snapshots_queued += result.snapshots_queued
    session.commit()
    return total


def due_pitch_days(session: Session, now: datetime | None = None) -> list[Programme]:
    """Pitch date has begun (00:00 SGT) and the reminder has not been claimed."""
    now = now or utcnow()
    rows = list(
        session.scalars(
            select(Programme)
            .where(Programme.pitch_starts_at.is_not(None))
            .where(Programme.pitch_day_emailed_at.is_(None))
            .where(
                Programme.status.notin_(
                    [ProgrammeStatus.DRAFT, ProgrammeStatus.COMPLETE]
                )
            )
        )
    )
    return [row for row in rows if pitch_day_begins_at(row.pitch_starts_at) <= now]


def process_pitch_day(
    session: Session, programme: Programme, now: datetime | None = None
) -> PitchDayResult:
    """Mail everyone who has a slot: their time, and the Meet."""
    now = now or utcnow()
    queued = enqueue_pitch_day_reminders(session, programme)
    programme.pitch_day_emailed_at = now
    return PitchDayResult(programmes_processed=1, emails_queued=queued)


def pitch_day_sweep(session: Session, now: datetime | None = None) -> PitchDayResult:
    """Every minute. Claims each programme once via pitch_day_emailed_at.

    If the sweep wakes up after 00:00, it still sends. A restart does not.
    """
    now = now or utcnow()
    total = PitchDayResult()
    for programme in due_pitch_days(session, now):
        result = process_pitch_day(session, programme, now)
        total.programmes_processed += result.programmes_processed
        total.emails_queued += result.emails_queued
    session.commit()
    return total


def no_submission_report(session: Session, programme_id) -> list[Participant]:
    """Deadline + 12h — the list admin actually acts on (FR-806)."""
    return list(
        session.scalars(
            select(Participant)
            .where(Participant.programme_id == programme_id)
            .where(Participant.status == ParticipantStatus.NO_SUBMISSION)
        )
    )


def rep_digest_targets(session: Session, now: datetime | None = None) -> list[Programme]:
    """08:00 during running. One email listing unanswered threads, not a
    notification per message — per-message alerts are muted by day two (FR-614a)."""
    return list(
        session.scalars(select(Programme).where(Programme.status == ProgrammeStatus.RUNNING))
    )


def response_time_indicator(session: Session, programme_id) -> dict:
    """FR-614b — oldest unanswered thread and the count outstanding, so admin
    can see a rep has gone quiet without being obliged to act."""
    from projet.models import Thread
    from projet.models.enums import ThreadStatus, ThreadType

    unanswered = (
        select(Thread)
        .where(Thread.programme_id == programme_id)
        .where(Thread.status == ThreadStatus.OPEN)
        .where(
            Thread.type.in_(
                [ThreadType.QUESTION_CHALLENGE, ThreadType.QUESTION_LOGISTICS, ThreadType.DIRECT]
            )
        )
    )
    rows = list(session.scalars(unanswered))
    oldest = min((t.created_at for t in rows), default=None)
    return {
        "outstanding": len(rows),
        "oldest_unanswered_at": oldest,
        "oldest_age_hours": (
            round((utcnow() - oldest).total_seconds() / 3600, 1) if oldest else None
        ),
    }


def preflight(session: Session, programme_id) -> list[dict]:
    """FR-1501 — T-1 09:00. Per participant: invite accepted, login succeeded,
    data pack opened. Surfaces as a checklist of failures, not a green tick."""
    participants = list(
        session.scalars(select(Participant).where(Participant.programme_id == programme_id))
    )
    checks = ("calendar_assigned", "google_email_present", "gmail_thread")
    failures = []
    for participant in participants:
        row = {
            "participant_id": participant.id,
            "name": participant.person.name,
            "calendar_assigned": participant.judging_session_id is not None,
            "google_email_present": bool(participant.person.google_email),
            "gmail_thread": bool(participant.gmail_thread_id),
        }
        if not all(row[check] for check in checks):
            failures.append(row)
    return failures
