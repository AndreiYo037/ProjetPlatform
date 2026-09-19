"""testimonial pdf — the file the company uploads to submit

The drafted wording is a helper. The PDF is the artefact they put their name
to, and the thing a participant downloads from the profile.

Revision ID: d4e5f6a7b8c9
Revises: c84a9ceb3d1e
Create Date: 2026-09-19 15:25:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c84a9ceb3d1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pdf_storage_key", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.drop_column("pdf_storage_key")
