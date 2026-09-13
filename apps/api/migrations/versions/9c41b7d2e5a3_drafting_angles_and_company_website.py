"""Drafting angles and the company website

A drafting run now produces two or three angles on the same role rather than
one statement, so the drafts have to stay grouped and keep the order they were
offered in. The website moves onto the company because it is what research
starts from and it is the same answer on every run.

Revision ID: 9c41b7d2e5a3
Revises: bf80f1a3cef9
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9c41b7d2e5a3"
down_revision = "bf80f1a3cef9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("company", sa.Column("website_url", sa.Text(), nullable=True))
    op.add_column(
        "problem_statement_draft",
        sa.Column("batch_id", sa.Uuid(), nullable=True),
    )
    # Existing drafts were single statements, so each is angle 1 of its own run.
    op.add_column(
        "problem_statement_draft",
        sa.Column("angle", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("problem_statement_draft", "angle")
    op.drop_column("problem_statement_draft", "batch_id")
    op.drop_column("company", "website_url")
