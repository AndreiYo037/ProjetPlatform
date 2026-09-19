"""Closing a programme, which is when the profile gets made.

Judge tags stay on the scoring card until this moment. Closing promotes them
to attested skills, issues credentials, and is the only act that writes those
claims — and any ready testimonials — onto a candidate's profile.

It runs once. A second close is refused, so a late card does not rewrite
anyone's profile after the company has already issued.
"""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Credential,
    Participant,
    Person,
    Programme,
    Score,
    Team,
    TeamMember,
    Testimonial,
)
from projet.models.enums import CredentialType, ProgrammeStatus
from projet.outbox.profile_effects import notify_candidate_profile_updated
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
    if programme.status == ProgrammeStatus.COMPLETE:
        raise CloseoutError("Already closed. Profiles were issued once.")
    from projet.services.schedule import programme_is_past

    # Closing before the week is over would bury an active challenge in every
    # listing that still treats status as gospel — and the week is not over
    # until the pitch/submit deadline has passed.
    if not programme_is_past(programme):
        raise CloseoutError(
            "This challenge is still running. Close it after the pitch day."
        )

    result = CloseoutResult()
    participants = db.scalars(
        select(Participant)
        .where(Participant.programme_id == programme.id)
        .where(Participant.excluded.is_(False))
    )
    for participant in participants:
        promoted = promote_score_skill_tags(db, participant.id)
        result.skills_promoted += promoted
        scored = was_scored(db, participant)
        ready_note = db.scalar(
            select(Testimonial.id)
            .where(Testimonial.participant_id == participant.id)
            .where(Testimonial.published_at.isnot(None))
            .where(Testimonial.pdf_storage_key.isnot(None))
            .limit(1)
        )
        if scored and (promoted or ready_note):
            person = db.get(Person, participant.person_id)
            if person is not None:
                bits = []
                if promoted:
                    bits.append(
                        f"{promoted} skill{'s' if promoted != 1 else ''} from "
                        f"{programme.title} are now on your Projet profile."
                    )
                if ready_note:
                    bits.append("A testimonial from the company is on your profile too.")
                notify_candidate_profile_updated(
                    db,
                    person=person,
                    participant_id=participant.id,
                    what=" ".join(bits),
                    key_suffix=f"closeout:{programme.id}",
                )
        if not scored:
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
