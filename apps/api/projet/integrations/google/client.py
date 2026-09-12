"""The Google seam: protocol, result types, errors, and driver selection.

One service account, domain-wide delegation, impersonating programs@projet.sg.
Scopes: gmail.send, calendar.events, drive.readonly, drive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from projet.config import get_settings
from projet.models.enums import AccessStatus

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
]


class GoogleError(RuntimeError):
    """Base for everything this module raises."""


class TransientGoogleError(GoogleError):
    """Rate limited, backend error, timeout — worth retrying."""


class PermanentGoogleError(GoogleError):
    """Malformed request, missing scope, deleted resource — retrying cannot help."""


@dataclass(slots=True)
class SentMessage:
    message_id: str
    thread_id: str


@dataclass(slots=True)
class CalendarEvent:
    event_id: str
    html_link: str | None = None
    meet_link: str | None = None


@dataclass(slots=True)
class DriveProbe:
    """Result of FR-802's accessibility check."""

    access_status: AccessStatus
    file_id: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.access_status == AccessStatus.OK


@dataclass(slots=True)
class DriveSnapshot:
    content: bytes
    mime_type: str
    filename: str
    fetched_at: datetime | None = None


@dataclass(slots=True)
class Attendee:
    email: str
    display_name: str | None = None


@dataclass(slots=True)
class EventSpec:
    summary: str
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    location: str | None = None
    attendees: list[Attendee] = field(default_factory=list)
    timezone: str = "Asia/Singapore"
    with_meet: bool = True


class GoogleClient(Protocol):
    def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        thread_id: str | None = None,
        references: str | None = None,
    ) -> SentMessage: ...

    def create_event(self, spec: EventSpec) -> CalendarEvent: ...

    def patch_event_attendees(
        self,
        event_id: str,
        *,
        add: list[Attendee] | None = None,
        remove: list[str] | None = None,
    ) -> CalendarEvent: ...

    def probe_drive_file(self, url: str) -> DriveProbe: ...

    def snapshot_drive_file(self, file_id: str, mime_type: str | None = None) -> DriveSnapshot: ...


_client: GoogleClient | None = None


def get_google_client() -> GoogleClient:
    """Real driver when credentials are configured, fake otherwise.

    A fresh clone and the whole test suite run against the fake; the real driver
    is selected by presence of a service account, or explicitly via
    PROJET_GOOGLE_DRIVER=real.
    """
    global _client
    if _client is None:
        if get_settings().use_real_google:
            from projet.integrations.google.real import RealGoogleClient

            _client = RealGoogleClient()
        else:
            from projet.integrations.google.fake import FakeGoogleClient

            _client = FakeGoogleClient()
    return _client


def set_google_client(client: GoogleClient | None) -> None:
    """Test seam."""
    global _client
    _client = client
