"""Add kickoff_event_id to programme

Revision ID: a1b2c3d4e5f6
Revises: e17b4c93da52
Create Date: 2026-09-17

Stores the Google Calendar event ID for the programme's kickoff call so
accepted participants can be added as attendees via the provisioning chain.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "e17b4c93da52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("programme", sa.Column("kickoff_event_id", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("programme", "kickoff_event_id")
