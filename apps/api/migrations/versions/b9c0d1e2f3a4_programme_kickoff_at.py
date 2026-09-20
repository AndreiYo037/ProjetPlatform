"""Company-chosen kickoff time on the start date.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-09-20

Kickoff is a call on the start date, at a time the company picks. Publish
is blocked until that time is set. The Meet is still created on publish.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programme",
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programme", "kickoff_at")
