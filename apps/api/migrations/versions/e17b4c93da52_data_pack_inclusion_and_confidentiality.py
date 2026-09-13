"""Data pack inclusion toggle and confidentiality flag

Revision ID: e17b4c93da52
Revises: c3f21a86d0b7
Create Date: 2026-09-13

A company curates the pack rather than accepting it: the seeded public sources
are a starting point it can clear, and anything it adds itself can be marked
confidential. Both default to the state existing rows are already in - included,
and not confidential - so nothing that was visible yesterday disappears today.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e17b4c93da52"
down_revision = "c3f21a86d0b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "data_pack_resource",
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "data_pack_resource",
        sa.Column("confidential", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("data_pack_resource", "confidential")
    op.drop_column("data_pack_resource", "included")
