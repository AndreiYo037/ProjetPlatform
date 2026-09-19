"""Claim column for the judging-day 00:00 reminder.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-09-20

At 00:00 SGT on the pitch date, booked candidates get their slot and the
cohort Meet. The timestamp claims that send so a restart cannot mail twice
and a sweep that wakes up after midnight still fires once.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programme",
        sa.Column("pitch_day_emailed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programme", "pitch_day_emailed_at")
