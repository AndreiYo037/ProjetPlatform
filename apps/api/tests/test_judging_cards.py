"""The submission card, and the scoring card it links to.

One card per participant, because everything is individual: the judge opens the
work, then scores the person who did it, with no group to disambiguate first.

Two rules are proved here rather than asserted in a docstring. Consent is
enforced at the query layer, so a participant who declined sharing is not in the
list a company sees. And a score belongs to the judge who gave it, so a second
judge on the same pitch starts from a blank card rather than editing the first
judge's.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from projet.db import get_session
from projet.integrations.google.client import set_google_client
from projet.main import create_app
from projet.models import (
    CompanyUser,
    PlatformUser,
    ProgrammeAssignment,
    Skill,
    SubmissionLink,
)
from projet.models.enums import (
    AccessStatus,
    ActorType,
    CompanyUserRole,
    SkillType,
    SubmissionSlot,
)
from projet.services.auth import SESSION_COOKIE, start_session
from projet.services.rubric import compose_rubric
from projet.services.teams import ensure_submission, ensure_team_for_participant
from tests.conftest import make_participant


@pytest.fixture
def client(session, google):
    set_google_client(google)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    set_google_client(None)


@pytest.fixture
def manager(session, company) -> CompanyUser:
    user = CompanyUser(
        company_id=company.id,
        name="Mo Manager",
        email="mo@acme.test",
        role=CompanyUserRole.OWNER,
    )
    session.add(user)
    session.flush()
    return user


def sign_in(client, session, user: CompanyUser) -> None:
    _, raw = start_session(session, actor_type=ActorType.COMPANY_USER, subject_id=user.id)
    client.cookies.set(SESSION_COOKIE, raw)


def submitted(session, participant, *, url="https://docs.google.com/document/d/abc/edit"):
    """A participant with work handed in, links checked and a snapshot taken.

    Provisioning already seeds the named slots, so this fills them rather than
    adding more - which is also what the real paste path does.
    """
    team = ensure_team_for_participant(session, participant)
    submission = ensure_submission(session, team)
    links = session.scalars(
        select(SubmissionLink).where(SubmissionLink.submission_id == submission.id)
    )
    for link in links:
        link.drive_url = url
        link.detected_filename = (
            "Churn dashboard" if link.slot is SubmissionSlot.ARTIFACT else "Memo"
        )
        link.access_status = AccessStatus.OK
        link.snapshot_key = f"snapshots/{submission.id}/{link.slot.value}.pdf"
    session.flush()
    return submission


@pytest.fixture
def cohort(session, programme, content_dir):
    compose_rubric(session, programme, content_dir)
    sam = make_participant(session, programme, name="Sam Student")
    sam.run_order = 2
    ada = make_participant(session, programme, name="Ada Analyst")
    ada.run_order = 1
    submitted(session, sam)
    submitted(session, ada)
    session.flush()
    return {"sam": sam, "ada": ada}


def test_the_cards_come_back_in_pitch_order(client, session, programme, manager, cohort):
    sign_in(client, session, manager)
    response = client.get(f"/programmes/{programme.id}/submissions")
    assert response.status_code == 200, response.text
    cards = response.json()
    assert [card["name"] for card in cards] == ["Ada Analyst", "Sam Student"]
    assert [card["run_order"] for card in cards] == [1, 2]


def test_a_card_carries_the_work_and_a_signed_snapshot(
    client, session, programme, manager, cohort
):
    sign_in(client, session, manager)
    card = next(
        c
        for c in client.get(f"/programmes/{programme.id}/submissions").json()
        if c["name"] == "Sam Student"
    )
    assert card["complete"] is True
    assert card["scored"] is False
    assert card["your_total"] is None
    link = card["links"][0]
    assert link["slot"] == "artifact"
    assert link["filename"] == "Churn dashboard"
    # The live document can be edited after the deadline; the snapshot cannot.
    assert link["snapshot_url"].startswith("/files/snapshots/")
    assert "sig=" in link["snapshot_url"]


def test_someone_who_declined_sharing_is_not_on_the_company_list(
    client, session, programme, manager, cohort
):
    quiet = make_participant(session, programme, name="Quiet Quinn", consent_share=False)
    submitted(session, quiet)
    sign_in(client, session, manager)

    names = {c["name"] for c in client.get(f"/programmes/{programme.id}/submissions").json()}
    assert "Quiet Quinn" not in names

    card = client.get(f"/programmes/{programme.id}/participants/{quiet.id}/score")
    assert card.status_code == 404


def test_the_scoring_card_carries_the_submission_and_the_anchors(
    client, session, programme, manager, cohort
):
    sign_in(client, session, manager)
    card = client.get(
        f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    ).json()
    assert card["name"] == "Sam Student"
    # The judge should not have to hold two tabs open during a pitch.
    assert card["submission"]["links"][0]["slot"] == "artifact"
    assert [c["slot"] for c in card["criteria"]] == [1, 2, 3, 4]
    assert all(c["value"] is None for c in card["criteria"])
    assert card["complete"] is False
    assert card["total"] is None
    # Slots 1 and 4 are the universal pair; they are what makes cohorts compare.
    assert [c["is_universal"] for c in card["criteria"]] == [True, False, False, True]


def test_a_total_arrives_only_once_all_four_are_rated(
    client, session, programme, manager, cohort
):
    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    criteria = client.get(url).json()["criteria"]

    partial = client.patch(
        url, json={"ratings": {criteria[0]["criterion_id"]: 5, criteria[1]["criterion_id"]: 4}}
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["total"] is None, "a half-scored card must not be ranked"
    assert partial.json()["complete"] is False

    whole = client.patch(
        url, json={"ratings": {criteria[2]["criterion_id"]: 3, criteria[3]["criterion_id"]: 2}}
    )
    assert whole.json()["total"] == 14
    assert whole.json()["complete"] is True

    listed = next(
        c
        for c in client.get(f"/programmes/{programme.id}/submissions").json()
        if c["name"] == "Sam Student"
    )
    assert listed["scored"] is True
    assert listed["your_total"] == 14


def test_a_rating_is_saved_as_it_is_given_and_can_be_changed(
    client, session, programme, manager, cohort
):
    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    first = client.get(url).json()["criteria"][0]["criterion_id"]

    client.patch(url, json={"ratings": {first: 2}})
    assert client.get(url).json()["criteria"][0]["value"] == 2
    client.patch(url, json={"ratings": {first: 5}})
    assert client.get(url).json()["criteria"][0]["value"] == 5


def test_a_rating_outside_one_to_five_is_refused(client, session, programme, manager, cohort):
    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    criterion = client.get(url).json()["criteria"][0]["criterion_id"]
    refused = client.patch(url, json={"ratings": {criterion: 7}})
    assert refused.status_code == 422
    assert "1 to 5" in refused.json()["detail"]


def test_a_criterion_from_another_programme_is_refused(
    client, session, programme, manager, cohort, role
):
    """A rubric is per programme, so a stray criterion id is a bug, not a score."""
    import uuid as _uuid

    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    refused = client.patch(url, json={"ratings": {str(_uuid.uuid4()): 4}})
    assert refused.status_code == 422
    assert "rubric" in refused.json()["detail"]


def test_the_referral_verdict_and_skill_tags_are_kept(
    client, session, programme, manager, cohort
):
    skill = Skill(name="SQL", slug="sql", type=SkillType.HARD)
    session.add(skill)
    session.flush()

    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    saved = client.patch(
        url, json={"would_refer": "yes", "skill_ids": [str(skill.id)]}
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["would_refer"] == "yes"
    assert saved.json()["skill_ids"] == [str(skill.id)]

    # Sent whole each time, so clearing one clears it.
    cleared = client.patch(url, json={"skill_ids": []})
    assert cleared.json()["skill_ids"] == []


def test_a_skill_that_does_not_exist_is_refused(client, session, programme, manager, cohort):
    import uuid as _uuid

    sign_in(client, session, manager)
    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    refused = client.patch(url, json={"skill_ids": [str(_uuid.uuid4())]})
    assert refused.status_code == 422
    assert "No such skill" in refused.json()["detail"]


def test_two_judges_keep_two_separate_cards(client, session, programme, manager, rep, cohort):
    session.add(
        ProgrammeAssignment(
            programme_id=programme.id, company_user_id=rep.id, can_score=True
        )
    )
    session.flush()

    url = f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    sign_in(client, session, manager)
    criteria = client.get(url).json()["criteria"]
    client.patch(url, json={"ratings": {c["criterion_id"]: 5 for c in criteria}})
    assert client.get(url).json()["total"] == 20

    sign_in(client, session, rep)
    fresh = client.get(url).json()
    assert fresh["total"] is None, "a judge must not inherit another judge's score"
    assert all(c["value"] is None for c in fresh["criteria"])


def test_a_rep_not_assigned_to_the_programme_sees_nothing(
    client, session, programme, rep, cohort
):
    """FR-015 - a rep sees only what they are assigned to, judging included."""
    sign_in(client, session, rep)
    assert client.get(f"/programmes/{programme.id}/submissions").status_code in (403, 404)


def test_an_assignment_without_scoring_rights_cannot_score(
    client, session, programme, rep, cohort
):
    session.add(
        ProgrammeAssignment(
            programme_id=programme.id, company_user_id=rep.id, can_score=False
        )
    )
    session.flush()
    sign_in(client, session, rep)
    response = client.get(
        f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
    )
    assert response.status_code == 403


def test_platform_staff_read_the_cohort_whole_but_do_not_score(
    client, session, programme, cohort
):
    """An admin watching the sitting is not the judge; the verdict is the
    company's, and a score with no judge behind it is worth nothing."""
    admin = PlatformUser(name="Andrei", email="andrei@projet.sg")
    session.add(admin)
    session.flush()
    quiet = make_participant(session, programme, name="Quiet Quinn", consent_share=False)
    submitted(session, quiet)

    _, raw = start_session(session, actor_type=ActorType.PLATFORM, subject_id=admin.id)
    client.cookies.set(SESSION_COOKIE, raw)

    names = {c["name"] for c in client.get(f"/programmes/{programme.id}/submissions").json()}
    assert "Quiet Quinn" in names

    refused = client.patch(
        f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score",
        json={"would_refer": "yes"},
    )
    assert refused.status_code == 403


def test_a_participant_cannot_read_a_scoring_card(client, session, programme, cohort):
    """FR-1004 - scores are never served to a participant-role session."""
    _, raw = start_session(
        session, actor_type=ActorType.PARTICIPANT, subject_id=cohort["sam"].person_id
    )
    client.cookies.set(SESSION_COOKIE, raw)
    assert client.get(f"/programmes/{programme.id}/submissions").status_code in (403, 404)
    assert (
        client.get(
            f"/programmes/{programme.id}/participants/{cohort['sam'].id}/score"
        ).status_code
        in (403, 404)
    )
