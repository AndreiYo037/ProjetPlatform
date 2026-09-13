"""The company logo.

A logo is the one company-supplied file that is meant to be seen by strangers:
it sits on the public challenge listing and in the directory, both of which are
read without a session. So unlike a CV or a data pack file it is served from a
stable, unsigned URL - an expiring signature on a brand mark would only produce
broken images on a cached page.

That makes the upload path the place to be careful. Only raster images are
accepted: an SVG is a document that can carry script, and serving one from our
own origin would hand a company user stored XSS against everyone who opens the
listing. PNG, JPEG and WebP cannot do that.
"""

from __future__ import annotations

import uuid

STORAGE_PREFIX = "logos"

MAX_LOGO_BYTES = 2 * 1024 * 1024
# Raster only, deliberately. See the module docstring on SVG.
LOGO_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
_MEDIA_BY_EXTENSION = {extension: media for media, extension in LOGO_TYPES.items()}


def is_stored_logo(value: str | None) -> bool:
    """A key we uploaded, as opposed to a link the company pasted."""
    return bool(value) and value.startswith(f"{STORAGE_PREFIX}/")  # type: ignore[union-attr]


def new_logo_key(company_id: uuid.UUID, content_type: str) -> str:
    """Random per upload, so a replaced logo is not served from a stale cache."""
    return f"{STORAGE_PREFIX}/{company_id}/{uuid.uuid4()}.{LOGO_TYPES[content_type]}"


def logo_media_type(key: str) -> str:
    """Recovered from the extension we chose, not from anything uploaded."""
    return _MEDIA_BY_EXTENSION.get(key.rsplit(".", 1)[-1], "application/octet-stream")


def logo_url(company_id: uuid.UUID, stored: str | None) -> str | None:
    """The address to render: our own route for an upload, the link otherwise."""
    if not stored:
        return None
    if is_stored_logo(stored):
        return f"/companies/{company_id}/logo"
    return stored
