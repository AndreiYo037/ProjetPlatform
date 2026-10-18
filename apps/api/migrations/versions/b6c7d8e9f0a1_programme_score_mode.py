"""Let a company score with its own overall score instead of the platform rubric.

Additive, with defaults, so every existing challenge keeps scoring on the rubric.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-10-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("programme", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("score_mode", sa.String(length=10), server_default="rubric", nullable=False)
        )
        batch_op.add_column(
            sa.Column("manual_score_max", sa.Integer(), server_default="100", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("programme", schema=None) as batch_op:
        batch_op.drop_column("manual_score_max")
        batch_op.drop_column("score_mode")
