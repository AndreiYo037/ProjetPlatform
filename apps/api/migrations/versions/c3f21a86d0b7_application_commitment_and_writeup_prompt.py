"""Application commitment and the role-specific writeup prompt.

Revision ID: c3f21a86d0b7
Revises: 9c41b7d2e5a3
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3f21a86d0b7"
down_revision = "9c41b7d2e5a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application", sa.Column("linkedin_url", sa.Text(), nullable=True))
    # Existing applications were taken before the declaration existed, so they
    # default to false rather than being back-dated into a yes nobody gave.
    op.add_column(
        "application",
        sa.Column(
            "availability_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("application", sa.Column("availability_note", sa.Text(), nullable=True))
    op.add_column("role_template", sa.Column("writeup_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("role_template", "writeup_prompt")
    op.drop_column("application", "availability_note")
    op.drop_column("application", "availability_confirmed")
    op.drop_column("application", "linkedin_url")
