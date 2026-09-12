"""Deadline snapshot (FR-804).

Locking the link field does not lock the document: a participant can keep
editing their deck for three days and the rep would see the edited version. The
snapshot is what is judged; the live link stays alongside it, labelled.

A failure here is alerted immediately rather than in a morning digest — with
judging the next day there is no recovery window.
"""

from __future__ import annotations

from projet.models import SubmissionLink
from projet.models.base import utcnow
from projet.models.enums import SnapshotStatus
from projet.outbox.effects import EffectContext, PermanentEffectError, effect
from projet.storage import get_storage

SNAPSHOT_EFFECT = "snapshot_submission_link"


@effect(SNAPSHOT_EFFECT)
def snapshot_submission_link(ctx: EffectContext) -> dict:
    link = ctx.session.get(SubmissionLink, ctx.row.subject_id)
    if link is None:
        raise PermanentEffectError(f"submission link {ctx.row.subject_id} no longer exists")

    file_id = ctx.payload.get("file_id") or link.drive_file_id
    if not file_id:
        link.snapshot_status = SnapshotStatus.FAILED
        raise PermanentEffectError("no drive file id to snapshot")

    mime = ctx.payload.get("mime") or link.detected_mime
    snapshot = ctx.google.snapshot_drive_file(file_id, mime)
    key = f"snapshots/{link.submission_id}/{link.slot.value}/{snapshot.filename}"
    get_storage().put(key, snapshot.content, snapshot.mime_type)

    link.snapshot_key = key
    link.snapshot_mime = snapshot.mime_type
    link.snapshot_bytes = len(snapshot.content)
    link.snapshot_at = snapshot.fetched_at or utcnow()
    link.snapshot_status = SnapshotStatus.OK
    return {"snapshot_key": key, "bytes": len(snapshot.content)}
