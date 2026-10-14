"""A typed memo on the submission.

Additive and nullable. Existing submissions keep NULL, which the completeness
rule treats as "handed in before the memo existed" and leaves valid.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-10-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.add_column(sa.Column("memo_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.drop_column("memo_text")
