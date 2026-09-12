"""Storage and signed URLs (section 8: not publicly addressable)."""

from __future__ import annotations

import time

import pytest

from projet.storage import LocalStorage, StorageError, sign_key, verify_signature


def test_round_trip(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.put("snapshots/a/artifact.pdf", b"%PDF-1.4")

    assert storage.exists("snapshots/a/artifact.pdf")
    assert storage.get("snapshots/a/artifact.pdf") == b"%PDF-1.4"


def test_a_key_cannot_escape_the_storage_root(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(StorageError, match="escapes storage root"):
        storage.put("../../etc/passwd", b"nope")


def test_missing_object_raises_rather_than_returning_empty(tmp_path):
    with pytest.raises(StorageError, match="missing object"):
        LocalStorage(tmp_path).get("nothing/here.pdf")


def test_signature_round_trips():
    token = sign_key("cvs/sam.pdf")
    assert verify_signature("cvs/sam.pdf", token)


def test_a_signature_does_not_transfer_to_another_key():
    token = sign_key("cvs/sam.pdf")
    assert not verify_signature("cvs/someone-else.pdf", token)


def test_an_expired_signature_is_rejected():
    token = sign_key("cvs/sam.pdf", ttl_seconds=-1)
    time.sleep(0.01)
    assert not verify_signature("cvs/sam.pdf", token)


@pytest.mark.parametrize("token", ["", "garbage", "notanumber.abc", "123"])
def test_malformed_tokens_are_rejected_without_raising(token):
    assert not verify_signature("cvs/sam.pdf", token)
