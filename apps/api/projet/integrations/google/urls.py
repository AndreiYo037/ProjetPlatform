"""Pure helpers for Drive URLs and export formats.

These carry the logic most likely to be wrong in the real driver and are unit
tested without a network: a participant pastes whatever Drive gave them, and a
misparse here is a dead link on judging day.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

# /file/d/<id>/view, /document/d/<id>/edit, /spreadsheets/d/<id>, /presentation/d/<id>
_PATH_ID = re.compile(r"/(?:file|document|spreadsheets|presentation|forms)/d/([A-Za-z0-9_-]{10,})")
# /folders/<id>
_FOLDER_ID = re.compile(r"/folders/([A-Za-z0-9_-]{10,})")

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES = "application/vnd.google-apps.presentation"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"

PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# FR-804: Docs and Slides export to PDF, Sheets to XLSX, everything else is
# downloaded as-is.
EXPORT_FORMATS = {
    GOOGLE_DOC: (PDF, "pdf"),
    GOOGLE_SLIDES: (PDF, "pdf"),
    GOOGLE_SHEET: (XLSX, "xlsx"),
}


def extract_file_id(url: str) -> str | None:
    """Pull the file id out of any Drive URL shape a participant might paste."""
    if not url:
        return None
    url = url.strip()

    match = _PATH_ID.search(url) or _FOLDER_ID.search(url)
    if match:
        return match.group(1)

    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("id")
    if query_id and query_id[0]:
        return query_id[0]

    # A bare id pasted on its own.
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", url):
        return url
    return None


def is_google_native(mime_type: str | None) -> bool:
    return bool(mime_type and mime_type.startswith("application/vnd.google-apps"))


def export_format(mime_type: str | None) -> tuple[str, str] | None:
    """Return (export mime, file extension) for a Google-native type, else None."""
    if not mime_type:
        return None
    return EXPORT_FORMATS.get(mime_type)


def snapshot_filename(base: str, mime_type: str | None) -> str:
    fmt = export_format(mime_type)
    if fmt is None:
        return base
    _, extension = fmt
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return f"{stem}.{extension}"
