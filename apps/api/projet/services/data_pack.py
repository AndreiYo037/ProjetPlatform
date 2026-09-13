"""The data pack: what a company hands over, and who gets to see it.

Three rules shape this module.

A source is excluded, not deleted. The seeded public sources come from the
role's registry, and a company that clears one it does not want should be able
to put it back without retyping a URL it never typed in the first place. So
`included` is a toggle, and what the company sees is the whole list with its
own choices visible in it.

An upload is never a public link. A file the company supplies lives in storage
and is served through an expiring signature, the same way a CV is, because the
point of the confidentiality flag is that the file is not something anyone can
forward.

And the pack is released, not advertised. The public listing gets the labels of
public sources only, so someone deciding whether to apply can see what kind of
data the week runs on; everything the company added shows up after a seat is
accepted, which is where the confidentiality acknowledgement bites.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from projet.models import DataPackResource, Programme
from projet.models.enums import Provenance
from projet.storage import sign_key

STORAGE_PREFIX = "data-pack"

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {
    "text/csv",
    "text/plain",
    "application/json",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "image/png",
    "image/jpeg",
}


def is_storage_key(value: str | None) -> bool:
    """Uploads are keys under our own prefix; everything else is a link."""
    return bool(value) and value.startswith(f"{STORAGE_PREFIX}/")  # type: ignore[union-attr]


def new_storage_key(programme_id: uuid.UUID, filename: str | None) -> str:
    """Namespaced per programme, with a random segment so two files of the same
    name do not overwrite each other."""
    safe = PurePosixPath(filename or "resource").name or "resource"
    return f"{STORAGE_PREFIX}/{programme_id}/{uuid.uuid4()}/{safe}"


def resource_url(value: str | None) -> str | None:
    """A signed, expiring URL for an upload; a company's own link untouched."""
    if value is None:
        return None
    if is_storage_key(value):
        return f"/files/{value}?sig={sign_key(value)}"
    return value


def released_resources(db: Session, programme_id: uuid.UUID) -> list[DataPackResource]:
    """What a participant inside the programme gets: the included list, whole."""
    return list(
        db.scalars(
            select(DataPackResource)
            .where(DataPackResource.programme_id == programme_id)
            .where(DataPackResource.included.is_(True))
            .order_by(DataPackResource.created_at)
        )
    )


def public_preview(db: Session, programme_id: uuid.UUID) -> list[str]:
    """Labels of the included public sources, and nothing else.

    Company-supplied material stays out of the preview whether or not it is
    flagged confidential: an applicant has not accepted anything yet, and the
    name of an internal export is itself information about the company.
    """
    return list(
        db.scalars(
            select(DataPackResource.label)
            .where(DataPackResource.programme_id == programme_id)
            .where(DataPackResource.included.is_(True))
            .where(DataPackResource.confidential.is_(False))
            .where(DataPackResource.provenance == Provenance.PUBLIC)
            .order_by(DataPackResource.created_at)
        )
    )


def sync_confidentiality_ack(db: Session, programme: Programme) -> None:
    """The flag on the programme follows from what is actually in the pack.

    Nobody should have to remember to tick it: adding one confidential file is
    the decision, and removing the last one undoes it.
    """
    programme.requires_confidentiality_ack = bool(
        db.scalar(
            select(DataPackResource.id)
            .where(DataPackResource.programme_id == programme.id)
            .where(DataPackResource.included.is_(True))
            .where(DataPackResource.confidential.is_(True))
            .limit(1)
        )
    )
