"""Object storage behind a protocol.

Section 8: CVs and snapshots are not publicly addressable and are served through
signed URLs scoped to the viewer. The local driver is for development; an
S3-compatible driver implements the same protocol.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Protocol

from projet.config import get_settings


class StorageError(RuntimeError):
    pass


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str | None = None) -> str: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Filesystem-backed. Keys are relative paths under storage_root."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or get_settings().storage_root)

    def _path(self, key: str) -> Path:
        # Keys come from our own code, but a traversal here would read the
        # filesystem, so resolve and confine rather than trusting the caller.
        candidate = (self.root / key).resolve()
        root = self.root.resolve()
        if not str(candidate).startswith(str(root)):
            raise StorageError(f"key escapes storage root: {key!r}")
        return candidate

    def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"missing object: {key!r}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


def sign_key(key: str, *, ttl_seconds: int | None = None) -> str:
    """Return an expiring signature for a storage key."""
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.signed_url_ttl_seconds
    expires = int(time.time()) + ttl
    message = f"{key}:{expires}".encode()
    signature = hmac.new(settings.storage_signing_key.encode(), message, hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def verify_signature(key: str, token: str) -> bool:
    try:
        expires_raw, signature = token.split(".", 1)
        expires = int(expires_raw)
    except (ValueError, AttributeError):
        return False
    if expires < time.time():
        return False
    settings = get_settings()
    expected = hmac.new(
        settings.storage_signing_key.encode(),
        f"{key}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_storage() -> Storage:
    return LocalStorage()
