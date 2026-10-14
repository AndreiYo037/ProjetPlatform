"""Telegram handle on the person and the application.

Additive and nullable: existing people and applications keep every value and
simply have no handle. New applications require one (enforced on apply, not
in the schema, so old rows stay valid).

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-10-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("person", schema=None) as batch_op:
        batch_op.add_column(sa.Column("telegram_handle", sa.String(length=64), nullable=True))
    with op.batch_alter_table("application", schema=None) as batch_op:
        batch_op.add_column(sa.Column("telegram_handle", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("application", schema=None) as batch_op:
        batch_op.drop_column("telegram_handle")
    with op.batch_alter_table("person", schema=None) as batch_op:
        batch_op.drop_column("telegram_handle")
