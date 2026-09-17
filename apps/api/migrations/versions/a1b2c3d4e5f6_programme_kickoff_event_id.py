"""Add kickoff Calendar fields to programme

Revision ID: a1b2c3d4e5f6
Revises: e17b4c93da52
Create Date: 2026-09-17

Stores the Google Calendar event ID and Meet link for the programme's kickoff
call. The event is created at publish time; accepted participants are patched
onto it via the provisioning chain.
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
    op.add_column("programme", sa.Column("kickoff_meet_link", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("programme", "kickoff_meet_link")
    op.drop_column("programme", "kickoff_event_id")
