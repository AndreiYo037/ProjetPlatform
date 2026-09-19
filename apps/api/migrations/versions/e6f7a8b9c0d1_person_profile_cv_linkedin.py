"""person profile cv and linkedin

A CV and LinkedIn URL belong on the person once they have an account — not only
on the application they first used to arrive. Update profile needs somewhere to
put them.

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-09-19 21:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e6f7a8b9c0d1"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("person", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cv_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("linkedin_url", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("person", schema=None) as batch_op:
        batch_op.drop_column("linkedin_url")
        batch_op.drop_column("cv_url")
