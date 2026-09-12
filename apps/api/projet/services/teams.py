"""Team resolution.

Every participant gets a Team, solo included, so a Submission always resolves
through one and hackathon pairs need no retrofit once live data exists.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import Participant, Programme, Submission, SubmissionLink, Team, TeamMember
from projet.models.enums import SubmissionSlot

DEFAULT_SLOTS = (SubmissionSlot.ARTIFACT, SubmissionSlot.MEMO)


def ensure_team_for_participant(session: Session, participant: Participant) -> Team:
    """The only sanctioned way to create a submission's owner."""
    existing = session.scalar(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.participant_id == participant.id)
    )
    if existing is not None:
        return existing

    team = Team(programme_id=participant.programme_id)
    session.add(team)
    session.flush()
    session.add(TeamMember(team_id=team.id, participant_id=participant.id))
    session.flush()
    return team


def add_team_member(session: Session, team: Team, participant: Participant) -> TeamMember:
    """Hackathon pairing. Enforces the programme's team_size_max rather than
    letting a pair form in a solo programme."""
    programme = session.get(Programme, team.programme_id)
    limit = programme.team_size_max if programme else 1
    current = len(list(session.scalars(select(TeamMember).where(TeamMember.team_id == team.id))))
    if current >= limit:
        raise ValueError(f"team is full: team_size_max is {limit}")
    member = TeamMember(team_id=team.id, participant_id=participant.id)
    session.add(member)
    session.flush()
    return member


def ensure_submission(session: Session, team: Team) -> Submission:
    """Seed the submission and its named slots — step 1 of provisioning."""
    submission = session.scalar(select(Submission).where(Submission.team_id == team.id))
    if submission is None:
        submission = Submission(team_id=team.id)
        session.add(submission)
        session.flush()

    # Query rather than reading submission.links: the relationship is stale on a
    # second call in the same session, and a stale read re-inserts every slot.
    existing = {
        link.slot
        for link in session.scalars(
            select(SubmissionLink).where(SubmissionLink.submission_id == submission.id)
        )
    }
    for slot in DEFAULT_SLOTS:
        if slot not in existing:
            session.add(SubmissionLink(submission_id=submission.id, slot=slot))
    session.flush()
    return submission
