"""E-signature fields on a testimonial.

Additive and nullable (the boolean has a default), so every existing
testimonial is simply unsigned until the company signs it.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-10-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import projet.models.base

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("signed_at", projet.models.base.UtcDateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("signed_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("signed_title", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("signature_key", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("signature_typed", sa.Boolean(), server_default="0", nullable=False)
        )
        batch_op.add_column(sa.Column("body_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("signed_ip", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("signed_user_agent", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.drop_column("signed_user_agent")
        batch_op.drop_column("signed_ip")
        batch_op.drop_column("body_hash")
        batch_op.drop_column("signature_typed")
        batch_op.drop_column("signature_key")
        batch_op.drop_column("signed_title")
        batch_op.drop_column("signed_name")
        batch_op.drop_column("signed_at")
