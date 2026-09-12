"""FR-015 — rep access is scoped by ProgrammeAssignment.

"A rep on the sustainability challenge cannot see the data challenge's
candidates." This is what makes enterprise viable later, where different
functions run different challenges and should not see each other's applicants.
"""

from __future__ import annotations

import uuid

from projet.api.deps import can_score_programme, can_see_programme, visible_programmes
from projet.models import CompanyUser, Programme, ProgrammeAssignment
from projet.models.enums import ActorType, CompanyUserRole
from projet.services.auth import Actor


def make_company_user(session, company, role: CompanyUserRole) -> CompanyUser:
    user = CompanyUser(
        company_id=company.id,
        name=role.value.title(),
        email=f"{role.value}-{uuid.uuid4().hex[:6]}@acme.test",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def actor_for(user: CompanyUser) -> Actor:
    return Actor(
        ActorType.COMPANY_USER,
        user.id,
        user.email,
        user.name,
        company_id=user.company_id,
        role=user.role.value,
    )


PLATFORM = Actor(ActorType.PLATFORM, uuid.uuid4(), "admin@projet.sg", "Admin", role="admin")


def test_platform_staff_see_everything(session, programme):
    assert can_see_programme(session, PLATFORM, programme)
    assert can_score_programme(session, PLATFORM, programme)


def test_an_owner_sees_every_programme_in_their_company(session, company, programme):
    owner = make_company_user(session, company, CompanyUserRole.OWNER)
    assert can_see_programme(session, actor_for(owner), programme)


def test_a_rep_sees_only_assigned_programmes(session, company, programme, role):
    rep = make_company_user(session, company, CompanyUserRole.REP)
    other = Programme(
        company_id=company.id, role_id=role.id, title="Data challenge", slug="data-challenge"
    )
    session.add(other)
    session.flush()
    session.add(ProgrammeAssignment(programme_id=programme.id, company_user_id=rep.id))
    session.flush()

    assert can_see_programme(session, actor_for(rep), programme)
    assert not can_see_programme(session, actor_for(rep), other), (
        "an unassigned programme in the same company must stay invisible"
    )


def test_a_rep_from_another_company_sees_nothing(session, programme, role):
    from projet.models import Company

    other_company = Company(name="Other Ltd", slug=f"other-{uuid.uuid4().hex[:6]}")
    session.add(other_company)
    session.flush()
    outsider = make_company_user(session, other_company, CompanyUserRole.OWNER)

    assert not can_see_programme(session, actor_for(outsider), programme)


def test_scoring_requires_the_can_score_flag(session, company, programme):
    rep = make_company_user(session, company, CompanyUserRole.REP)
    session.add(
        ProgrammeAssignment(programme_id=programme.id, company_user_id=rep.id, can_score=False)
    )
    session.flush()

    assert can_see_programme(session, actor_for(rep), programme)
    assert not can_score_programme(session, actor_for(rep), programme)


def test_a_viewer_is_read_only_but_can_see(session, company, programme):
    viewer = make_company_user(session, company, CompanyUserRole.VIEWER)
    session.add(
        ProgrammeAssignment(programme_id=programme.id, company_user_id=viewer.id, can_score=False)
    )
    session.flush()

    assert can_see_programme(session, actor_for(viewer), programme)
    assert not can_score_programme(session, actor_for(viewer), programme)


def test_visible_programmes_matches_the_per_programme_check(session, company, programme, role):
    """The list query and the single-programme check must not disagree, or a
    programme shows in a list and 404s when opened."""
    rep = make_company_user(session, company, CompanyUserRole.REP)
    other = Programme(company_id=company.id, role_id=role.id, title="Data challenge", slug="data-2")
    session.add(other)
    session.flush()
    session.add(ProgrammeAssignment(programme_id=programme.id, company_user_id=rep.id))
    session.flush()

    listed = {p.id for p in session.scalars(visible_programmes(session, actor_for(rep)))}
    assert listed == {programme.id}

    owner = make_company_user(session, company, CompanyUserRole.OWNER)
    owner_listed = {p.id for p in session.scalars(visible_programmes(session, actor_for(owner)))}
    assert owner_listed == {programme.id, other.id}


def test_participants_get_no_programmes_from_the_company_query(session, programme):
    participant_actor = Actor(ActorType.PARTICIPANT, uuid.uuid4(), "s@x.test", "Sam")
    listed = list(session.scalars(visible_programmes(session, participant_actor)))
    assert listed == []
