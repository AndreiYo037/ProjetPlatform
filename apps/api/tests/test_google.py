"""Google client logic.

The networked paths in real.py have never run against Google — there are no
credentials in the build environment. What is tested here is everything around
them, which is where the mistakes that cost a cohort actually live: a misparsed
Drive URL, a Meet link that never gets requested, a cohort's email addresses
leaked to each other, a rate limit treated as permanent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from projet.integrations.google.client import (
    Attendee,
    EventSpec,
    PermanentGoogleError,
    TransientGoogleError,
)
from projet.integrations.google.real import (
    build_event_body,
    build_message,
    classify_http_error,
    extract_meet_link,
)
from projet.integrations.google.urls import (
    export_format,
    extract_file_id,
    is_google_native,
    snapshot_filename,
)
from projet.models.enums import AccessStatus

FILE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz01234567"


class FakeResponse:
    def __init__(self, status):
        self.status = status


class FakeHttpError(Exception):
    def __init__(self, status, reason=""):
        self.resp = FakeResponse(status)
        self.content = (
            b'{"error":{"errors":[{"reason":"%s"}]}}' % reason.encode() if reason else b"{}"
        )


@pytest.mark.parametrize(
    "url",
    [
        f"https://docs.google.com/document/d/{FILE_ID}/edit?usp=sharing",
        f"https://drive.google.com/file/d/{FILE_ID}/view",
        f"https://drive.google.com/open?id={FILE_ID}",
        f"https://docs.google.com/spreadsheets/d/{FILE_ID}",
        f"https://docs.google.com/presentation/d/{FILE_ID}/edit#slide=id.p",
        f"https://drive.google.com/drive/folders/{FILE_ID}",
        FILE_ID,
    ],
)
def test_every_drive_url_shape_a_participant_might_paste(url):
    assert extract_file_id(url) == FILE_ID


@pytest.mark.parametrize("url", ["", "https://example.com/report.pdf", "not a url", "   "])
def test_non_drive_urls_do_not_yield_a_file_id(url):
    assert extract_file_id(url) is None


def test_export_formats_follow_fr_804():
    """Docs and Slides to PDF, Sheets to XLSX, everything else as-is."""
    assert export_format("application/vnd.google-apps.document")[0] == "application/pdf"
    assert export_format("application/vnd.google-apps.presentation")[0] == "application/pdf"
    assert export_format("application/vnd.google-apps.spreadsheet")[0].endswith("sheet")
    assert export_format("application/pdf") is None
    assert is_google_native("application/vnd.google-apps.document")


def test_snapshot_filename_takes_the_exported_extension():
    assert (
        snapshot_filename("deck.gslides", "application/vnd.google-apps.presentation") == "deck.pdf"
    )
    assert snapshot_filename("data.csv", "text/csv") == "data.csv"


def test_calendar_events_never_expose_the_cohort_to_each_other():
    """FR-1600 — the Google default is to show every guest to every other guest,
    which would hand each participant the whole cohort's email addresses."""
    spec = EventSpec(
        summary="Judging",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(hours=2),
        attendees=[Attendee("a@x.test"), Attendee("b@x.test")],
    )
    body = build_event_body(spec)

    assert body["guestsCanSeeOtherGuests"] is False
    assert body["guestsCanInviteOthers"] is False


def test_meet_link_is_requested_for_every_session():
    """FR-1400 — conferenceData with a request id is the only way to get one."""
    spec = EventSpec(
        summary="Kickoff",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(hours=1),
    )
    body = build_event_body(spec)
    request = body["conferenceData"]["createRequest"]

    assert request["conferenceSolutionKey"]["type"] == "hangoutsMeet"
    assert request["requestId"]


def test_meet_link_is_read_back_off_the_created_event():
    event = {
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "phone", "uri": "tel:+65"},
                {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
            ]
        }
    }
    assert extract_meet_link(event) == "https://meet.google.com/abc-defg-hij"
    assert extract_meet_link({"hangoutLink": "https://meet.google.com/x"}) is not None
    assert extract_meet_link({}) is None


def test_threading_headers_are_set_so_gmail_keeps_one_thread():
    """Section 7.2 — nine touchpoints hang off one thread. threadId alone puts
    the message in the thread but clients render it as a new conversation."""
    import base64

    raw = build_message(
        sender="programs@projet.sg",
        to="sam@school.test",
        subject="Your submission",
        html_body="<p>Hi</p>",
        references="<abc@mail.gmail.com>",
    )
    decoded = base64.urlsafe_b64decode(raw).decode()

    assert "In-Reply-To: <abc@mail.gmail.com>" in decoded
    assert "References: <abc@mail.gmail.com>" in decoded
    assert "text/html" in decoded


@pytest.mark.parametrize(
    "status,reason,expected",
    [
        (429, "rateLimitExceeded", TransientGoogleError),
        (403, "rateLimitExceeded", TransientGoogleError),
        (403, "userRateLimitExceeded", TransientGoogleError),
        (403, "insufficientPermissions", PermanentGoogleError),
        (500, "backendError", TransientGoogleError),
        (503, "", TransientGoogleError),
        (404, "notFound", PermanentGoogleError),
        (400, "badRequest", PermanentGoogleError),
    ],
)
def test_http_errors_split_into_retryable_and_not(status, reason, expected):
    """403 is ambiguous: rate limiting and permission denial share it. Getting
    this wrong either drops a real email or burns five retries on a dead one."""
    assert isinstance(classify_http_error(FakeHttpError(status, reason)), expected)


def test_fake_client_reports_a_denied_link_in_the_words_a_participant_needs(google):
    url = f"https://drive.google.com/file/d/{FILE_ID}/view"
    google.stage_denied(url)
    probe = google.probe_drive_file(url)

    assert probe.access_status == AccessStatus.DENIED
    assert not probe.ok
    assert "Anyone with the link can view" in (probe.message or "")


def test_fake_client_removes_an_attendee_without_touching_the_rest(google):
    spec = EventSpec(
        summary="Judging",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(hours=2),
        attendees=[],
    )
    event = google.create_event(spec)
    google.patch_event_attendees(event.event_id, add=[Attendee("a@x.test"), Attendee("b@x.test")])
    google.patch_event_attendees(event.event_id, remove=["a@x.test"])

    emails = [a["email"] for a in google.events[event.event_id]["attendees"]]
    assert emails == ["b@x.test"]
