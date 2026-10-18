"""A judge can give their own overall score instead of using the rubric.

The company-wide scoring mode added in b6c7d8e9f0a1 was replaced by this
per-score option, so its two columns are dropped. Both are additive or safe:
no challenge ever stored anything in them.

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-10-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("score", schema=None) as batch_op:
        batch_op.add_column(sa.Column("manual_total", sa.Integer(), nullable=True))
    with op.batch_alter_table("programme", schema=None) as batch_op:
        batch_op.drop_column("manual_score_max")
        batch_op.drop_column("score_mode")


def downgrade() -> None:
    with op.batch_alter_table("programme", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("score_mode", sa.String(length=10), server_default="rubric", nullable=False)
        )
        batch_op.add_column(
            sa.Column("manual_score_max", sa.Integer(), server_default="100", nullable=False)
        )
    with op.batch_alter_table("score", schema=None) as batch_op:
        batch_op.drop_column("manual_total")
