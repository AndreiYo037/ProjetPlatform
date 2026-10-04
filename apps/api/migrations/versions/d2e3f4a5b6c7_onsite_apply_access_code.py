"""On-site apply access code on the programme.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-05

Walk-up on-site challenges need a shared code so only people in the room can
apply. Online programmes leave the column null.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programme",
        sa.Column("apply_access_code", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programme", "apply_access_code")
