"""Certificates: who gets Merit, who gets Completion, and the PDF.

One certificate per team, printed with every member's name together. Only a
team a company actually scored gets one, so a certificate never means "was on
the list".

The rule, per challenge, over the scored teams:

- fewer than 20 teams: the top half (rounded up) get Merit;
- 20 or more: the top 10 get Merit;
- everyone else scored gets Completion.

Ties at the cutoff share the higher title. A company can also give a team a
placing ("3rd Place") or set its title by hand; that is an override on top of
the rule, not a change to it.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import (
    Certificate,
    Company,
    Participant,
    Person,
    Programme,
    Score,
    Team,
    TeamMember,
)
from projet.models.base import utcnow
from projet.services.certificate_pdf import render_certificate_pdf
from projet.services.scoring import criteria_for
from projet.storage import get_storage

MERIT = "merit"
COMPLETION = "completion"
MANUAL_MAX = 100
MERIT_CAP = 10
CAP_FROM = 20


def merit_count(entries: int) -> int:
    """How many top places earn Merit among this many scored teams."""
    if entries <= 0:
        return 0
    if entries < CAP_FROM:
        return math.ceil(entries / 2)
    return MERIT_CAP


@dataclass
class TeamAward:
    """What a company can set by hand for one team."""

    names: list[str] | None = None
    extra_participant_ids: list[uuid.UUID] = field(default_factory=list)
    tier: str | None = None
    place_label: str | None = None


@dataclass
class Planned:
    team_id: uuid.UUID
    names: list[str]
    tier: str
    place_label: str | None
    rank: int
    joint: bool
    entries: int
    share: float
    recipient_person_ids: list[str]
    applied_teams: int
    submitted_teams: int


def _team_shares(db: Session, programme: Programme) -> dict[uuid.UUID, float]:
    """Each scored team's average share of the maximum, across its judges."""
    needed = len(criteria_for(db, programme.id))
    rows = db.scalars(
        select(Score).join(Team, Team.id == Score.team_id).where(Team.programme_id == programme.id)
    )
    shares: dict[uuid.UUID, list[float]] = {}
    for score in rows:
        if score.manual_total is not None:
            value, top = score.manual_total, MANUAL_MAX
        elif score.total is not None:
            value, top = score.total, needed * 5
        else:
            continue
        if top <= 0:
            continue
        shares.setdefault(score.team_id, []).append(value / top)
    return {team: sum(vals) / len(vals) for team, vals in shares.items()}


def _team_members(db: Session, team_id: uuid.UUID) -> list[Participant]:
    return list(
        db.scalars(
            select(Participant)
            .join(TeamMember, TeamMember.participant_id == Participant.id)
            .where(TeamMember.team_id == team_id)
            .where(Participant.excluded.is_(False))
        )
    )


def plan_certificates(
    db: Session,
    programme: Programme,
    *,
    awards: dict[uuid.UUID, TeamAward] | None = None,
    applied_teams: int | None = None,
    submitted_teams: int | None = None,
) -> list[Planned]:
    """Who would get what. Reads only. `awards` is keyed by team id."""
    awards = awards or {}
    shares = _team_shares(db, programme)
    ordered = sorted(shares.items(), key=lambda item: -round(item[1], 6))
    entries = len(ordered)
    cutoff = round(ordered[merit_count(entries) - 1][1], 6) if entries else 0.0
    team_count = len(list(db.scalars(select(Team.id).where(Team.programme_id == programme.id))))

    plans: list[Planned] = []
    for team_id, share in ordered:
        rounded = round(share, 6)
        rank = 1 + sum(1 for _, other in ordered if round(other, 6) > rounded)
        joint = sum(1 for _, other in ordered if round(other, 6) == rounded) > 1
        members = _team_members(db, team_id)
        award = awards.get(team_id, TeamAward())

        names = [n.strip() for n in (award.names or []) if n.strip()]
        if not names:
            names = [p.name for p in (db.get(Person, m.person_id) for m in members) if p]
        person_ids = {str(m.person_id) for m in members}
        for participant_id in award.extra_participant_ids:
            extra = db.get(Participant, participant_id)
            if extra is not None and extra.programme_id == programme.id:
                person_ids.add(str(extra.person_id))

        tier = MERIT if rounded >= cutoff else COMPLETION
        if award.tier in (MERIT, COMPLETION):
            tier = award.tier
        place = award.place_label.strip()[:40] if award.place_label else None
        if place:
            tier = MERIT  # a placing is a Merit by definition
        plans.append(
            Planned(
                team_id=team_id,
                names=names,
                tier=tier,
                place_label=place,
                rank=rank,
                joint=joint,
                entries=entries,
                share=share,
                recipient_person_ids=sorted(person_ids),
                applied_teams=applied_teams if applied_teams is not None else team_count,
                submitted_teams=submitted_teams if submitted_teams is not None else entries,
            )
        )
    return plans


def _logo_bytes(company: Company | None) -> bytes | None:
    from projet.services.branding import is_stored_logo

    if company is None or not is_stored_logo(company.logo_url):
        return None
    try:
        return get_storage().get(company.logo_url)
    except Exception:
        return None


def issue_certificates(
    db: Session,
    programme: Programme,
    plans: list[Planned],
    *,
    event_name: str | None = None,
    event_date: str | None = None,
) -> list[Certificate]:
    """Write the certificates and their PDFs. Asking again updates in place, so
    fixing a name or a placing is a re-issue of the same certificate."""
    company = db.get(Company, programme.company_id)
    company_name = company.name if company else ""
    logo = _logo_bytes(company)
    issued: list[Certificate] = []
    for plan in plans:
        row = db.scalar(
            select(Certificate)
            .where(Certificate.programme_id == programme.id)
            .where(Certificate.team_id == plan.team_id)
        )
        if row is None:
            row = Certificate(programme_id=programme.id, team_id=plan.team_id)
            db.add(row)
        row.tier = plan.tier
        row.place_label = plan.place_label
        row.rank = plan.rank
        row.entries = plan.entries
        row.names = plan.names
        row.recipient_person_ids = plan.recipient_person_ids
        row.applied_teams = plan.applied_teams
        row.submitted_teams = plan.submitted_teams
        row.event_name = event_name
        row.event_date = event_date
        row.issued_at = utcnow()
        db.flush()
        pdf = render_certificate_pdf(
            names=plan.names,
            tier=plan.tier,
            programme_title=programme.title,
            company_name=company_name,
            logo_png=logo,
            place_label=plan.place_label,
            rank=plan.rank,
            entries=plan.entries,
            applied_teams=plan.applied_teams,
            submitted_teams=plan.submitted_teams,
            event_name=event_name,
            event_date=event_date,
            joint=plan.joint,
        )
        key = f"certificates/{programme.id}/{plan.team_id}.pdf"
        get_storage().put(key, pdf, "application/pdf")
        row.pdf_storage_key = key
        issued.append(row)
    db.flush()
    return issued
