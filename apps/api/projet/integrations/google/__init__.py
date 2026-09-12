"""Google Workspace integration."""

from projet.integrations.google.client import (
    CalendarEvent,
    DriveProbe,
    DriveSnapshot,
    GoogleClient,
    PermanentGoogleError,
    SentMessage,
    TransientGoogleError,
    get_google_client,
)

__all__ = [
    "CalendarEvent",
    "DriveProbe",
    "DriveSnapshot",
    "GoogleClient",
    "PermanentGoogleError",
    "SentMessage",
    "TransientGoogleError",
    "get_google_client",
]
