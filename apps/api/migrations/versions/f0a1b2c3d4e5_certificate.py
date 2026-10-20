"""Certificates: one per team, Merit or Completion, with the names it prints.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-10-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import projet.models.base

revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("place_label", sa.String(length=40), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("entries", sa.Integer(), nullable=True),
        sa.Column("names", projet.models.base.JSONEncoded(), nullable=False),
        sa.Column("recipient_person_ids", projet.models.base.JSONEncoded(), nullable=False),
        sa.Column("applied_teams", sa.Integer(), nullable=True),
        sa.Column("submitted_teams", sa.Integer(), nullable=True),
        sa.Column("event_name", sa.String(length=120), nullable=True),
        sa.Column("event_date", sa.String(length=40), nullable=True),
        sa.Column("pdf_storage_key", sa.String(length=300), nullable=True),
        sa.Column("issued_at", projet.models.base.UtcDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["programme_id"], ["programme.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("programme_id", "team_id"),
    )


def downgrade() -> None:
    op.drop_table("certificate")
