# ruff: noqa: F811
"""Certificates: the Merit rule, placings, issuing, and who sees them."""

from __future__ import annotations

import pytest

from projet.models import Score
from projet.services.certificates import (
    COMPLETION,
    MERIT,
    TeamAward,
    merit_count,
    plan_certificates,
)
from projet.services.teams import ensure_team_for_participant
from tests.conftest import make_participant
from tests.test_profile_closeout import (  # noqa: F401  (fixtures)
    client,
    manager,
    sat,
    score_fully,
    sign_in_company,
    sign_in_participant,
    skill,
)


@pytest.mark.parametrize(
    ("entries", "expected"),
    [(0, 0), (1, 1), (2, 1), (4, 2), (5, 3), (19, 10), (20, 10), (21, 10), (40, 10)],
)
def test_the_merit_rule(entries, expected):
    assert merit_count(entries) == expected


def _scored_teams(session, programme, manager, values):
    people = []
    for index, value in enumerate(values):
        participant = make_participant(session, programme, name=f"Person {index}")
        team = ensure_team_for_participant(session, participant)
        session.add(Score(team_id=team.id, scorer_id=manager.id, manual_total=value))
        people.append((participant, team))
    session.flush()
    return people


def test_the_top_half_get_merit_and_the_rest_completion(session, programme, manager):
    people = _scored_teams(session, programme, manager, [90, 85, 77, 68])
    plans = {p.team_id: p for p in plan_certificates(session, programme)}
    tiers = [plans[team.id].tier for _, team in people]
    assert tiers == [MERIT, MERIT, COMPLETION, COMPLETION]
    assert [plans[team.id].rank for _, team in people] == [1, 2, 3, 4]
    assert all(plans[team.id].entries == 4 for _, team in people)


def test_ties_at_the_cutoff_share_merit(session, programme, manager):
    people = _scored_teams(session, programme, manager, [83, 83, 72, 70, 70])
    plans = {p.team_id: p for p in plan_certificates(session, programme)}
    # Five entries, so three Merits: the two 83s and the 72.
    assert [plans[t.id].tier for _, t in people] == [MERIT, MERIT, MERIT, COMPLETION, COMPLETION]
    assert plans[people[0][1].id].joint is True
    assert plans[people[0][1].id].rank == plans[people[1][1].id].rank == 1
    assert plans[people[2][1].id].rank == 3
    assert plans[people[3][1].id].rank == 4


def test_a_cutoff_tie_pulls_everyone_on_it_into_merit(session, programme, manager):
    people = _scored_teams(session, programme, manager, [90, 80, 80, 60])
    plans = {p.team_id: p for p in plan_certificates(session, programme)}
    # Four entries, two Merits; the 80s tie for second, so both get it.
    assert [plans[t.id].tier for _, t in people] == [MERIT, MERIT, MERIT, COMPLETION]


def test_an_unscored_team_gets_nothing(session, programme, manager):
    _scored_teams(session, programme, manager, [90])
    silent = make_participant(session, programme, name="Silent")
    ensure_team_for_participant(session, silent)
    session.flush()
    plans = plan_certificates(session, programme)
    assert len(plans) == 1


def test_a_placing_makes_it_merit_and_names_can_be_set(session, programme, manager):
    people = _scored_teams(session, programme, manager, [90, 85, 77, 68])
    jade, jade_team = people[2]
    plans = plan_certificates(
        session,
        programme,
        awards={
            jade_team.id: TeamAward(
                names=["Jade Yap", "Siaw Min En Alena"], place_label="3rd Place"
            )
        },
    )
    mine = next(p for p in plans if p.team_id == jade_team.id)
    assert mine.tier == MERIT
    assert mine.place_label == "3rd Place"
    assert mine.names == ["Jade Yap", "Siaw Min En Alena"]


def test_close_issues_certificates_and_participants_see_their_own(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    assert client.post(f"/programmes/{programme.id}/close").status_code == 200

    issued = client.get(f"/programmes/{programme.id}/certificates").json()
    assert len(issued) == 2
    assert {row["tier"] for row in issued} <= {MERIT, COMPLETION}

    sign_in_participant(client, session, sat["sam"])
    mine = client.get("/me/certificates")
    assert mine.status_code == 200
    rows = mine.json()
    assert len(rows) == 1
    assert rows[0]["names"] == [sat["sam"].person.name]
    assert "rank" not in rows[0]
    pdf = client.get(rows[0]["pdf_url"])
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_reissuing_with_a_placing_and_names_updates_the_same_certificate(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")

    body = {
        "teams": [
            {
                "participant_id": str(sat["ada"].id),
                "names": ["Ada Analyst", "Grace Teammate"],
                "place_label": "3rd Place",
            }
        ],
        "event_name": "Hack n Hire 2026",
        "event_date": "17 October 2026",
    }
    plan = client.post(f"/programmes/{programme.id}/certificates/plan", json=body)
    assert plan.status_code == 200, plan.text
    ada_plan = next(p for p in plan.json() if p["names"] == ["Ada Analyst", "Grace Teammate"])
    assert ada_plan["tier"] == MERIT and ada_plan["place_label"] == "3rd Place"

    before = client.get(f"/programmes/{programme.id}/certificates").json()
    again = client.post(f"/programmes/{programme.id}/certificates/issue", json=body)
    assert again.status_code == 200, again.text
    after = client.get(f"/programmes/{programme.id}/certificates").json()
    assert len(after) == len(before) == 2
    updated = next(row for row in after if row["place_label"] == "3rd Place")
    assert updated["names"] == ["Ada Analyst", "Grace Teammate"]


def test_planning_changes_nothing(client, session, programme, manager, sat, skill):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")
    client.post(f"/programmes/{programme.id}/certificates/plan", json={})
    assert len(client.get(f"/programmes/{programme.id}/certificates").json()) == 2


def test_a_company_cannot_issue_before_the_challenge_closes(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    refused = client.post(f"/programmes/{programme.id}/certificates/issue", json={})
    assert refused.status_code == 409


def test_a_participant_cannot_plan_or_issue(client, session, programme, sat):
    sign_in_participant(client, session, sat["sam"])
    assert client.post(f"/programmes/{programme.id}/certificates/plan", json={}).status_code in (
        403,
        404,
    )
    assert client.post(f"/programmes/{programme.id}/certificates/issue", json={}).status_code in (
        403,
        404,
    )


def test_long_team_names_wrap_onto_two_lines_and_still_render():
    from reportlab.pdfgen import canvas

    from projet.services.certificate_pdf import _name_lines, render_certificate_pdf

    names = [
        "Osby Angelo Pua De Leon",
        "Kylie Khoo Hoi Yann",
        "Muhammad Abdul Rauf Bin Abdul Malik",
    ]
    lines = _name_lines(canvas.Canvas("/dev/null"), names)
    assert len(lines) == 2
    assert lines[1].startswith("and ")
    assert _name_lines(canvas.Canvas("/dev/null"), ["Jade Yap", "Siaw Min En Alena"]) == [
        "Jade Yap and Siaw Min En Alena"
    ]
    pdf = render_certificate_pdf(
        names=names, tier="completion", programme_title="A challenge", company_name="Acme"
    )
    assert pdf.startswith(b"%PDF")


def test_certificate_emails_go_once_per_issue_and_dry_run_sends_nothing(
    client, session, programme, manager, sat, skill, google
):
    from projet.outbox.worker import run_once

    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")
    run_once(session, google)

    dry = client.post(f"/programmes/{programme.id}/certificates/notify", json={"dry_run": True})
    assert dry.status_code == 200, dry.text
    assert dry.json()["queued"] == 0
    assert sorted(dry.json()["recipients"]) == sorted(
        [sat["sam"].person.name, sat["ada"].person.name]
    )
    run_once(session, google)
    assert not [c for c in google.calls_of("send_email") if "Certificate" in c.payload["subject"]]

    sent = client.post(f"/programmes/{programme.id}/certificates/notify", json={})
    assert sent.json()["queued"] == 2
    client.post(f"/programmes/{programme.id}/certificates/notify", json={})
    run_once(session, google)
    mails = [c for c in google.calls_of("send_email") if "Certificate" in c.payload["subject"]]
    assert len(mails) == 2
    body = mails[0].payload["html_body"]
    assert "attached as a PDF" in body
    assert "profile" not in body.lower()
    assert mails[0].payload["attachments"] and mails[0].payload["attachments"][0].endswith(".pdf")


def test_submitter_only_skips_teammates_added_to_the_certificate(
    client, session, programme, manager, sat, skill
):
    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")
    mate = make_participant(session, programme, name="Sam Teammate")
    client.post(
        f"/programmes/{programme.id}/certificates/issue",
        json={
            "teams": [
                {"participant_id": str(sat["sam"].id), "extra_participant_ids": [str(mate.id)]}
            ]
        },
    )
    everyone = client.post(
        f"/programmes/{programme.id}/certificates/notify", json={"dry_run": True}
    ).json()["recipients"]
    only = client.post(
        f"/programmes/{programme.id}/certificates/notify",
        json={"dry_run": True, "submitter_only": True},
    ).json()["recipients"]
    assert "Sam Teammate" in everyone
    assert "Sam Teammate" not in only
    assert sat["sam"].person.name in only


def test_the_certificate_pdf_is_attached_to_the_message():
    import base64
    from email import message_from_bytes

    from projet.integrations.google.client import Attachment
    from projet.integrations.google.real import build_message

    raw = build_message(
        sender="projet@example.com",
        to="a@example.com",
        subject="Your certificate",
        html_body="<p>Hi</p>",
        attachments=[Attachment(filename="Certificate.pdf", content=b"%PDF-1.4 test")],
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    parts = [p for p in message.walk() if p.get_filename()]
    assert [p.get_filename() for p in parts] == ["Certificate.pdf"]
    assert parts[0].get_content_type() == "application/pdf"
    assert parts[0].get_payload(decode=True) == b"%PDF-1.4 test"


def test_the_company_can_see_where_its_certificate_emails_stand(
    client, session, programme, manager, sat, skill, google
):
    from projet.outbox.worker import run_once

    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")
    client.post(f"/programmes/{programme.id}/certificates/notify", json={})
    pending = client.get(f"/programmes/{programme.id}/certificates/emails").json()
    assert len(pending) == 2 and {row["status"] for row in pending} == {"pending"}
    run_once(session, google)
    done = client.get(f"/programmes/{programme.id}/certificates/emails").json()
    assert {row["status"] for row in done} == {"done"}
    assert all(row["sent_at"] for row in done)


def test_the_submitter_is_greeted_by_the_name_on_the_certificate(
    client, session, programme, manager, sat, skill, google
):
    from projet.outbox.worker import run_once

    sign_in_company(client, session, manager)
    score_fully(client, programme, sat["sam"], skill)
    score_fully(client, programme, sat["ada"])
    client.post(f"/programmes/{programme.id}/close")
    client.post(
        f"/programmes/{programme.id}/certificates/issue",
        json={"teams": [{"participant_id": str(sat["sam"].id), "names": ["Samuel Real Name"]}]},
    )
    run_once(session, google)
    client.post(f"/programmes/{programme.id}/certificates/notify", json={"submitter_only": True})
    run_once(session, google)
    mails = [c for c in google.calls_of("send_email") if "Certificate" in c.payload["subject"]]
    sam = next(c for c in mails if c.payload["to"] == sat["sam"].person.contact_email)
    assert sam.payload["html_body"].startswith("<p>Hi Samuel Real Name,</p>")
    assert sam.payload["attachments"]
