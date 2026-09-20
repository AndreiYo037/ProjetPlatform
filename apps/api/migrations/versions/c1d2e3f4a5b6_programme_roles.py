"""A challenge can cover more than one role.

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-09-20

Each extra role adds that role's slot 2 and slot 3 to the scorecard.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "programme_role" in sa.inspect(bind).get_table_names():
        op.drop_table("programme_role")
    op.create_table(
        "programme_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["programme_id"], ["programme.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("programme_id", "role_id", name="uq_programme_role_pair"),
        sa.UniqueConstraint("programme_id", "position", name="uq_programme_role_position"),
    )
    for programme_id, role_id in bind.execute(sa.text("SELECT id, role_id FROM programme")):
        bind.execute(
            sa.text(
                "INSERT INTO programme_role (id, programme_id, role_id, position) "
                "VALUES (:id, :programme_id, :role_id, 0)"
            ),
            {
                "id": str(uuid.uuid4()),
                "programme_id": str(programme_id),
                "role_id": str(role_id),
            },
        )
    with op.batch_alter_table("rubric_criterion") as batch:
        # Alembic's SQLite batch helper prefixes ck_<table>_, so pass the suffix.
        batch.drop_constraint("slot_range", type_="check")
        batch.add_column(
            sa.Column("family", sa.Integer(), nullable=False, server_default="2")
        )
        batch.add_column(sa.Column("role_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("lane", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_foreign_key(
            "fk_rubric_criterion_role_id_role",
            "role",
            ["role_id"],
            ["id"],
        )
    op.execute("UPDATE rubric_criterion SET family = slot, lane = 0")
    op.execute(
        """
        UPDATE rubric_criterion
        SET role_id = (
            SELECT programme.role_id FROM programme
            WHERE programme.id = rubric_criterion.programme_id
        )
        WHERE family IN (2, 3)
        """
    )
    with op.batch_alter_table("rubric_criterion") as batch:
        batch.alter_column("family", server_default=None)
        batch.alter_column("lane", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("rubric_criterion") as batch:
        batch.drop_constraint("fk_rubric_criterion_role_id_role", type_="foreignkey")
        batch.drop_column("lane")
        batch.drop_column("role_id")
        batch.drop_column("family")
        batch.create_check_constraint("slot_range", "slot between 1 and 4")
    op.drop_table("programme_role")
