"""Closing a programme, which is when the profile gets made.

Everything before this point is transient: a Score is a judge's working note, a
ScoreSkillTag is something one person observed on one evening. Closing the
programme is what turns that into the durable thing the participant keeps - an
attested skill with a named practitioner behind it, and a credential that can be
verified by someone who was never in the room.

So closing is deliberately a single explicit act rather than a status that
drifts in on a timer. It is the moment the platform makes claims on a
participant's behalf, and a claim made by a cron job at 2am is a claim nobody
decided to make.

Re-running is safe and is expected: a judge who scores late should still reach
the profile, so closing again promotes what is new and leaves the rest alone.
"""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import Credential, Participant, Programme, Score, Team, TeamMember
from projet.models.enums import CredentialType, ProgrammeStatus
from projet.services.profile import promote_score_skill_tags

# The company closes when they are ready. Draft is the exception: nothing has
# been published yet, so there is no programme to close.


class CloseoutError(RuntimeError):
    pass


def new_verify_code() -> str:
    """Short enough to read down a phone, long enough not to be guessed.

    A credential nobody can check is a picture of a certificate, so this is the
    part that has to be real: 160 bits, url-safe, unique.
    """
    return secrets.token_urlsafe(20)


def issue_credential(
    db: Session, participant: Participant, credential_type: CredentialType
) -> Credential | None:
    """One per person per programme per type. Returns None if already issued."""
    existing = db.scalar(
        select(Credential)
        .where(Credential.person_id == participant.person_id)
        .where(Credential.programme_id == participant.programme_id)
        .where(Credential.type == credential_type)
    )
    if existing is not None:
        return None
    credential = Credential(
        person_id=participant.person_id,
        programme_id=participant.programme_id,
        type=credential_type,
        verify_code=new_verify_code(),
    )
    db.add(credential)
    db.flush()
    return credential


def was_scored(db: Session, participant: Participant) -> bool:
    """Did a judge actually sit through this pitch?

    A completion credential says someone did the work and presented it. Issuing
    one to a participant no judge scored would make the credential mean
    attendance, and a credential that means attendance is worth nothing to the
    person holding it.
    """
    return bool(
        db.scalar(
            select(Score.id)
            .join(Team, Team.id == Score.team_id)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.participant_id == participant.id)
            .where(Score.total.isnot(None))
            .limit(1)
        )
    )


class CloseoutResult:
    def __init__(self) -> None:
        self.skills_promoted = 0
        self.credentials_issued = 0
        self.participants_closed = 0
        self.skipped: list[str] = []


def close_programme(db: Session, programme: Programme) -> CloseoutResult:
    """Promote every judge tag, issue every earned credential, then mark it done."""
    if programme.status == ProgrammeStatus.DRAFT:
        raise CloseoutError("Publish the challenge first.")

    result = CloseoutResult()
    participants = db.scalars(
        select(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.excluded.is_(False))
    )
    for participant in participants:
        result.skills_promoted += promote_score_skill_tags(db, participant.id)
        if not was_scored(db, participant):
            result.skipped.append(str(participant.id))
            continue
        result.participants_closed += 1
        if issue_credential(db, participant, CredentialType.COMPLETION) is not None:
            result.credentials_issued += 1
        if participant.is_winner and (
            issue_credential(db, participant, CredentialType.TOP_PERFORMER) is not None
        ):
            result.credentials_issued += 1

    programme.status = ProgrammeStatus.COMPLETE
    db.flush()
    return result


def credentials_for(db: Session, person_id: uuid.UUID) -> list[Credential]:
    return list(
        db.scalars(
            select(Credential)
            .where(Credential.person_id == person_id)
            .order_by(Credential.issued_at.desc())
        )
    )
