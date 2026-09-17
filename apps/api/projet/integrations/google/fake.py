"""In-memory Google client.

Every flow test runs against this, and so does a fresh clone with no
credentials. It records what it was asked to do so a test can assert on the
call, and it can be primed to fail so retry behaviour is exercised.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from projet.integrations.google.client import (
    Attendee,
    CalendarEvent,
    DriveProbe,
    DriveSnapshot,
    EventSpec,
    SentMessage,
)
from projet.integrations.google.real import build_event_body
from projet.integrations.google.urls import export_format, extract_file_id, snapshot_filename
from projet.models.base import utcnow
from projet.models.enums import AccessStatus


@dataclass
class FakeCall:
    method: str
    payload: dict[str, Any]


@dataclass
class FakeGoogleClient:
    calls: list[FakeCall] = field(default_factory=list)
    events: dict[str, dict] = field(default_factory=dict)
    # url -> DriveProbe, so a test can stage a denied or missing link
    drive_files: dict[str, DriveProbe] = field(default_factory=dict)
    fail_next: Exception | None = None
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def _next_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids):04d}"

    def _maybe_fail(self) -> None:
        if self.fail_next is not None:
            error, self.fail_next = self.fail_next, None
            raise error

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        thread_id: str | None = None,
        references: str | None = None,
    ) -> SentMessage:
        self._maybe_fail()
        self.calls.append(
            FakeCall(
                "send_email",
                {
                    "to": to,
                    "subject": subject,
                    "thread_id": thread_id,
                    "html_body": html_body,
                },
            )
        )
        return SentMessage(
            message_id=self._next_id("msg"), thread_id=thread_id or self._next_id("thread")
        )

    def create_event(self, spec: EventSpec) -> CalendarEvent:
        self._maybe_fail()
        body = build_event_body(spec)  # shares the real body builder, so FR-1600 is exercised
        event_id = self._next_id("evt")
        self.events[event_id] = body
        self.calls.append(FakeCall("create_event", {"event_id": event_id, "body": body}))
        return CalendarEvent(
            event_id=event_id,
            html_link=f"https://calendar.google.com/event?eid={event_id}",
            meet_link=f"https://meet.google.com/{event_id}" if spec.with_meet else None,
        )

    def patch_event_attendees(
        self,
        event_id: str,
        *,
        add: list[Attendee] | None = None,
        remove: list[str] | None = None,
    ) -> CalendarEvent:
        self._maybe_fail()
        event = self.events.setdefault(event_id, {"attendees": []})
        attendees = event.get("attendees", [])
        if remove:
            dropped = {e.lower() for e in remove}
            attendees = [a for a in attendees if a.get("email", "").lower() not in dropped]
        if add:
            known = {a.get("email", "").lower() for a in attendees}
            attendees += [
                {"email": a.email, "displayName": a.display_name}
                for a in add
                if a.email.lower() not in known
            ]
        event["attendees"] = attendees
        event["guestsCanSeeOtherGuests"] = False
        self.calls.append(
            FakeCall(
                "patch_event_attendees",
                {"event_id": event_id, "add": add, "remove": remove},
            )
        )
        return CalendarEvent(event_id=event_id)

    def probe_drive_file(self, url: str) -> DriveProbe:
        self._maybe_fail()
        self.calls.append(FakeCall("probe_drive_file", {"url": url}))
        if url in self.drive_files:
            return self.drive_files[url]
        file_id = extract_file_id(url)
        if not file_id:
            return DriveProbe(
                access_status=AccessStatus.NOT_FOUND,
                message="That does not look like a Google Drive link.",
            )
        return DriveProbe(
            access_status=AccessStatus.OK,
            file_id=file_id,
            filename=f"{file_id}.pdf",
            mime_type="application/pdf",
        )

    def snapshot_drive_file(self, file_id: str, mime_type: str | None = None) -> DriveSnapshot:
        self._maybe_fail()
        self.calls.append(
            FakeCall("snapshot_drive_file", {"file_id": file_id, "mime_type": mime_type})
        )
        fmt = export_format(mime_type)
        out_mime = fmt[0] if fmt else (mime_type or "application/octet-stream")
        return DriveSnapshot(
            content=b"%PDF-1.4 fake snapshot",
            mime_type=out_mime,
            filename=snapshot_filename(f"{file_id}.bin", mime_type),
            fetched_at=utcnow(),
        )

    # -- test helpers ---------------------------------------------------------

    def calls_of(self, method: str) -> list[FakeCall]:
        return [c for c in self.calls if c.method == method]

    def stage_denied(self, url: str) -> None:
        self.drive_files[url] = DriveProbe(
            access_status=AccessStatus.DENIED,
            file_id=extract_file_id(url),
            message="We can't open this — set sharing to 'Anyone with the link can view'.",
        )
