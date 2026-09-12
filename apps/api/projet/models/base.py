"""Column conventions shared by every model.

Portability rules, applied uniformly (see docs/decisions.md):
  * UUID primary keys via sqlalchemy.Uuid  -> UUID on Postgres, CHAR(36) on SQLite
  * Enums as plain VARCHAR (native_enum=False), validated in Python -> no Postgres enum migrations
  * List fields as JSON, JSONB on Postgres
  * Every datetime is timezone-aware and stored UTC (FR-1602)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, TypeDecorator, TypeEngine


class JSONEncoded(TypeDecorator):
    """JSONB on Postgres, JSON everywhere else.

    A TypeDecorator rather than JSON().with_variant() so Alembic autogenerate
    renders the type by name and the migration keeps JSONB on the production
    dialect instead of silently downgrading to JSON.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


JSONList = JSONEncoded
JSONDict = JSONEncoded


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_pk() -> Any:
    from sqlalchemy.orm import mapped_column

    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def enum_column(python_enum: type, **kwargs: Any) -> TypeEngine:
    """Plain VARCHAR rather than a native Postgres enum, and deliberately
    without a CHECK constraint either.

    Adding a status value to a native enum (or to a CHECK) needs a migration to
    alter the type, and every status vocabulary in this schema will grow.
    validate_strings rejects unknown values at the Python boundary, which is
    where they would come from.
    """
    return Enum(
        python_enum,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
        **kwargs,
    )


class UtcDateTime(TypeDecorator):
    """Timezone-aware UTC on every dialect.

    Postgres hands back aware datetimes; SQLite hands back naive ones, so the
    same comparison against utcnow() works in production and raises in tests.
    Normalising on the way in and out removes the difference, and enforces
    FR-1602's "all datetimes stored UTC" rather than trusting callers.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None:
            # A naive datetime reaching the database is a bug upstream, but
            # guessing anything other than UTC would silently shift it.
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


TimestampTZ = UtcDateTime()
