"""project fields: one description, ongoing, file attachments

The four narrative columns become one `description`, because a case study
reads as prose and four boxes made it a form. Existing text is folded into
that one column rather than dropped — the columns go, the writing does not.

`kind` goes from both tables: a project has no type field (the associated
experience carries that), and a link is either a URL or an uploaded file,
which `storage_key` already says.

Revision ID: c84a9ceb3d1e
Revises: 552df2a6b0f2
Create Date: 2026-09-18 12:35:54.713652
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "c84a9ceb3d1e"
down_revision = "552df2a6b0f2"
branch_labels = None
depends_on = None


def _fold(problem, approach, contribution, outcome) -> str | None:
    """Four fields into one readable block, keeping every word that was there."""
    parts: list[str] = []
    if problem:
        parts.append(str(problem).strip())
    if approach:
        parts.append(str(approach).strip())
    if contribution:
        try:
            lines = json.loads(contribution) if isinstance(contribution, str) else contribution
        except (TypeError, ValueError):
            lines = []
        parts.extend(f"- {line}" for line in lines or [])
    if outcome:
        parts.append(str(outcome).strip())
    return "\n\n".join(p for p in parts if p) or None


def upgrade() -> None:
    # Add first, backfill, then drop: the old writing survives the change.
    with op.batch_alter_table("project_entry", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("associated_experience", sa.String(length=300), nullable=True)
        )
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("ongoing", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, organisation_name, problem, approach, contribution, outcome "
            "FROM project_entry"
        )
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text(
                "UPDATE project_entry SET associated_experience = :org, description = :description "
                "WHERE id = :id"
            ),
            {
                "id": row[0],
                "org": row[1],
                "description": _fold(row[2], row[3], row[4], row[5]),
            },
        )

    with op.batch_alter_table("project_entry", schema=None) as batch_op:
        batch_op.alter_column("ongoing", server_default=None)
        batch_op.drop_column("organisation_name")
        batch_op.drop_column("problem")
        batch_op.drop_column("approach")
        batch_op.drop_column("contribution")
        batch_op.drop_column("outcome")
        batch_op.drop_column("kind")

    with op.batch_alter_table("project_link", schema=None) as batch_op:
        batch_op.add_column(sa.Column("storage_key", sa.String(length=400), nullable=True))
        batch_op.add_column(sa.Column("filename", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("content_type", sa.String(length=120), nullable=True))
        # A file row has no URL.
        batch_op.alter_column("url", existing_type=sa.TEXT(), nullable=True)
        batch_op.drop_column("kind")


def downgrade() -> None:
    """Reversible in shape. The split of description back into four fields is
    not recoverable, so the whole block lands in `problem`."""
    with op.batch_alter_table("project_link", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.VARCHAR(length=6), nullable=False, server_default="doc")
        )
        batch_op.drop_column("content_type")
        batch_op.drop_column("filename")
        batch_op.drop_column("storage_key")

    # Rows with no URL were file attachments and have nowhere to go back to.
    op.execute(sa.text("DELETE FROM project_link WHERE url IS NULL"))
    with op.batch_alter_table("project_link", schema=None) as batch_op:
        batch_op.alter_column("url", existing_type=sa.TEXT(), nullable=False)
        batch_op.alter_column("kind", server_default=None)

    with op.batch_alter_table("project_entry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organisation_name", sa.VARCHAR(length=300), nullable=True))
        batch_op.add_column(sa.Column("problem", sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column("approach", sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column("outcome", sa.TEXT(), nullable=True))
        batch_op.add_column(
            sa.Column("contribution", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("kind", sa.VARCHAR(length=11), nullable=False, server_default="independent")
        )

    op.execute(
        sa.text(
            "UPDATE project_entry SET organisation_name = associated_experience, "
            "problem = description"
        )
    )
    op.execute(
        sa.text("UPDATE project_entry SET kind = 'programme' WHERE participant_id IS NOT NULL")
    )

    with op.batch_alter_table("project_entry", schema=None) as batch_op:
        batch_op.alter_column("contribution", server_default=None)
        batch_op.alter_column("kind", server_default=None)
        batch_op.drop_column("description")
        batch_op.drop_column("ongoing")
        batch_op.drop_column("associated_experience")
