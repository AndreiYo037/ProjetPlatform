"""Pitching date, duration, and shared Meet on the programme.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-20

The company picks when pitching starts and how long each pitch is (including
turn-over). Individual slots are JudgingSession rows; the Meet lives on the
programme so every booked participant joins the same room.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("programme", sa.Column("pitch_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("programme", sa.Column("pitch_duration_minutes", sa.Integer(), nullable=True))
    op.add_column("programme", sa.Column("pitch_event_id", sa.String(length=300), nullable=True))
    op.add_column("programme", sa.Column("pitch_meet_link", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("programme", "pitch_meet_link")
    op.drop_column("programme", "pitch_event_id")
    op.drop_column("programme", "pitch_duration_minutes")
    op.drop_column("programme", "pitch_starts_at")
