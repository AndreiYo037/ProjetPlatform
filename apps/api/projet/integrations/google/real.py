"""The real Google Workspace driver.

UNVERIFIED AGAINST LIVE APIS. No service-account credentials exist in the build
environment, so the networked paths here have never executed against Google.
What is tested is the logic that surrounds them: URL parsing, export-format
selection, event payload construction, and HttpError classification. Treat the
first live run as the verification step.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from email.message import EmailMessage
from typing import Any

from projet.config import get_settings
from projet.integrations.google.client import (
    SCOPES,
    Attendee,
    CalendarEvent,
    DriveProbe,
    DriveSnapshot,
    EventSpec,
    PermanentGoogleError,
    SentMessage,
    TransientGoogleError,
)
from projet.integrations.google.urls import (
    export_format,
    extract_file_id,
    snapshot_filename,
)
from projet.models.base import utcnow
from projet.models.enums import AccessStatus

CALENDAR_ID = "primary"
TRANSIENT_STATUSES = {403, 429, 500, 502, 503, 504}
# 403 is ambiguous: rate limiting and permission denial share it, so the reason
# string decides. These are the rate-limit reasons Google documents.
TRANSIENT_403_REASONS = {
    "rateLimitExceeded",
    "userRateLimitExceeded",
    "backendError",
    "internalError",
}


def classify_http_error(error: Any) -> Exception:
    """Map a googleapiclient HttpError to our transient/permanent split.

    Retrying a permanent failure burns four more attempts and delays the alert;
    treating a rate limit as permanent drops a real email on the floor.
    """
    status = getattr(getattr(error, "resp", None), "status", None)
    reason = ""
    try:
        payload = json.loads(getattr(error, "content", b"{}") or b"{}")
        errors = payload.get("error", {}).get("errors") or [{}]
        reason = errors[0].get("reason", "")
    except (ValueError, AttributeError, IndexError, TypeError):
        reason = ""

    if status == 403:
        if reason in TRANSIENT_403_REASONS:
            return TransientGoogleError(f"{status} {reason}: {error}")
        return PermanentGoogleError(f"{status} {reason}: {error}")
    if status in TRANSIENT_STATUSES:
        return TransientGoogleError(f"{status} {reason}: {error}")
    return PermanentGoogleError(f"{status} {reason}: {error}")


def build_event_body(spec: EventSpec) -> dict:
    """Construct the Calendar insert body.

    Two settings here are requirements, not defaults:
      * guestsCanSeeOtherGuests False (FR-1600) — the Google default exposes
        every participant's email address to the whole cohort
      * conferenceData with a request id (FR-1400) — the only way to get a Meet
        link, and it needs conferenceDataVersion=1 on the call
    """
    body: dict[str, Any] = {
        "summary": spec.summary,
        "description": spec.description,
        "location": spec.location,
        "start": {"dateTime": spec.starts_at.isoformat(), "timeZone": spec.timezone},
        "end": {"dateTime": spec.ends_at.isoformat(), "timeZone": spec.timezone},
        "attendees": [{"email": a.email, "displayName": a.display_name} for a in spec.attendees],
        "guestsCanSeeOtherGuests": False,
        "guestsCanInviteOthers": False,
        "guestsCanModify": False,
    }
    if spec.with_meet:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": f"projet-{int(datetime.now().timestamp() * 1000)}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
    return {k: v for k, v in body.items() if v is not None}


def extract_meet_link(event: dict) -> str | None:
    conference = event.get("conferenceData") or {}
    for entry in conference.get("entryPoints") or []:
        if entry.get("entryPointType") == "video":
            return entry.get("uri")
    return event.get("hangoutLink")


def build_message(
    *,
    sender: str,
    to: str,
    subject: str,
    html_body: str,
    references: str | None = None,
) -> str:
    """Base64url-encoded RFC822.

    Gmail threads on threadId only when the headers agree: without In-Reply-To
    and References the message lands in the thread but clients render it as a
    new conversation, which breaks the nine touchpoints all hanging off one thread.
    """
    message = EmailMessage()
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    if references:
        message["In-Reply-To"] = references
        message["References"] = references
    message.set_content("This message requires an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


class RealGoogleClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.subject = self.settings.google_delegated_subject
        self._services: dict[str, Any] = {}

    # -- wiring ---------------------------------------------------------------

    def _credentials(self):  # type: ignore[no-untyped-def]
        from google.oauth2 import service_account

        if self.settings.google_service_account_json:
            info = json.loads(self.settings.google_service_account_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif self.settings.google_service_account_file:
            creds = service_account.Credentials.from_service_account_file(
                str(self.settings.google_service_account_file), scopes=SCOPES
            )
        else:
            raise PermanentGoogleError(
                "no Google service account configured; set PROJET_GOOGLE_SERVICE_ACCOUNT_FILE "
                "or PROJET_GOOGLE_SERVICE_ACCOUNT_JSON, or run with PROJET_GOOGLE_DRIVER=fake"
            )
        return creds.with_subject(self.subject)

    def _service(self, name: str, version: str):  # type: ignore[no-untyped-def]
        key = f"{name}:{version}"
        if key not in self._services:
            from googleapiclient.discovery import build

            self._services[key] = build(
                name, version, credentials=self._credentials(), cache_discovery=False
            )
        return self._services[key]

    # -- Gmail ----------------------------------------------------------------

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        thread_id: str | None = None,
        references: str | None = None,
    ) -> SentMessage:
        from googleapiclient.errors import HttpError

        body: dict[str, Any] = {
            "raw": build_message(
                sender=self.subject,
                to=to,
                subject=subject,
                html_body=html_body,
                references=references,
            )
        }
        if thread_id:
            body["threadId"] = thread_id
        try:
            sent = (
                self._service("gmail", "v1")
                .users()
                .messages()
                .send(userId="me", body=body)
                .execute()
            )
        except HttpError as error:
            raise classify_http_error(error) from error
        return SentMessage(message_id=sent["id"], thread_id=sent.get("threadId", ""))

    # -- Calendar -------------------------------------------------------------

    def create_event(self, spec: EventSpec) -> CalendarEvent:
        from googleapiclient.errors import HttpError

        try:
            created = (
                self._service("calendar", "v3")
                .events()
                .insert(
                    calendarId=CALENDAR_ID,
                    body=build_event_body(spec),
                    conferenceDataVersion=1 if spec.with_meet else 0,
                    sendUpdates="externalOnly",
                )
                .execute()
            )
        except HttpError as error:
            raise classify_http_error(error) from error
        return CalendarEvent(
            event_id=created["id"],
            html_link=created.get("htmlLink"),
            meet_link=extract_meet_link(created),
        )

    def patch_event_attendees(
        self,
        event_id: str,
        *,
        add: list[Attendee] | None = None,
        remove: list[str] | None = None,
    ) -> CalendarEvent:
        """FR-811c/FR-1601 — sendUpdates externalOnly so backfilling one
        attendee does not re-notify the whole cohort."""
        from googleapiclient.errors import HttpError

        events = self._service("calendar", "v3").events()
        try:
            current = events.get(calendarId=CALENDAR_ID, eventId=event_id).execute()
            attendees = current.get("attendees", [])
            if remove:
                dropped = {email.lower() for email in remove}
                attendees = [a for a in attendees if a.get("email", "").lower() not in dropped]
            if add:
                known = {a.get("email", "").lower() for a in attendees}
                for attendee in add:
                    if attendee.email.lower() not in known:
                        attendees.append(
                            {"email": attendee.email, "displayName": attendee.display_name}
                        )
            patched = events.patch(
                calendarId=CALENDAR_ID,
                eventId=event_id,
                body={"attendees": attendees, "guestsCanSeeOtherGuests": False},
                sendUpdates="externalOnly",
            ).execute()
        except HttpError as error:
            raise classify_http_error(error) from error
        return CalendarEvent(
            event_id=patched["id"],
            html_link=patched.get("htmlLink"),
            meet_link=extract_meet_link(patched),
        )

    # -- Drive ----------------------------------------------------------------

    def probe_drive_file(self, url: str) -> DriveProbe:
        """FR-802 — the check that stops five dead links on judging day."""
        from googleapiclient.errors import HttpError

        file_id = extract_file_id(url)
        if not file_id:
            return DriveProbe(
                access_status=AccessStatus.NOT_FOUND,
                message="That does not look like a Google Drive link.",
            )
        try:
            meta = (
                self._service("drive", "v3")
                .files()
                .get(fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True)
                .execute()
            )
        except HttpError as error:
            status = getattr(getattr(error, "resp", None), "status", None)
            if status == 404:
                return DriveProbe(
                    access_status=AccessStatus.NOT_FOUND,
                    file_id=file_id,
                    message="We can't find that file — check the link is complete.",
                )
            if status == 403:
                return DriveProbe(
                    access_status=AccessStatus.DENIED,
                    file_id=file_id,
                    message=(
                        "We can't open this — set sharing to 'Anyone with the link can view'."
                    ),
                )
            raise classify_http_error(error) from error
        return DriveProbe(
            access_status=AccessStatus.OK,
            file_id=meta["id"],
            filename=meta.get("name"),
            mime_type=meta.get("mimeType"),
        )

    def snapshot_drive_file(self, file_id: str, mime_type: str | None = None) -> DriveSnapshot:
        """FR-804 — the frozen copy that is what actually gets judged."""
        from googleapiclient.errors import HttpError

        files = self._service("drive", "v3").files()
        try:
            if mime_type is None:
                meta = files.get(
                    fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True
                ).execute()
                mime_type = meta.get("mimeType")
                filename = meta.get("name", file_id)
            else:
                filename = file_id

            fmt = export_format(mime_type)
            if fmt is not None:
                export_mime, _ = fmt
                content = files.export(fileId=file_id, mimeType=export_mime).execute()
                return DriveSnapshot(
                    content=content,
                    mime_type=export_mime,
                    filename=snapshot_filename(filename, mime_type),
                    fetched_at=utcnow(),
                )
            content = files.get_media(fileId=file_id, supportsAllDrives=True).execute()
        except HttpError as error:
            raise classify_http_error(error) from error
        return DriveSnapshot(
            content=content,
            mime_type=mime_type or "application/octet-stream",
            filename=filename,
            fetched_at=utcnow(),
        )
