"""The testimonial letter's own parts: recipients, sign-off and company details.

All nullable and additive. Existing testimonials keep their body and simply
fall back to the participant's name and the author's account details.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-10-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import projet.models.base

revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("recipients", projet.models.base.JSONEncoded(), nullable=True)
        )
        batch_op.add_column(sa.Column("signoff_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("signoff_title", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("signoff_company", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("company_details", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("testimonial", schema=None) as batch_op:
        batch_op.drop_column("company_details")
        batch_op.drop_column("signoff_company")
        batch_op.drop_column("signoff_title")
        batch_op.drop_column("signoff_name")
        batch_op.drop_column("recipients")
