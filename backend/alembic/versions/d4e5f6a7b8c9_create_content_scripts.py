"""create content script versions

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-05 03:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_scripts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("calendar_item_id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("working_title", sa.String(length=255), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("talking_points", sa.JSON(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("alt_titles", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calendar_item_id"], ["content_calendar_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "calendar_item_id", "version", name="uq_content_scripts_item_version"
        ),
    )
    op.create_index(
        op.f("ix_content_scripts_calendar_item_id"),
        "content_scripts",
        ["calendar_item_id"],
    )
    op.create_index(
        op.f("ix_content_scripts_creator_id"),
        "content_scripts",
        ["creator_id"],
    )
    op.create_index(
        op.f("ix_content_scripts_input_hash"),
        "content_scripts",
        ["input_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_content_scripts_input_hash"),
        table_name="content_scripts",
    )
    op.drop_index(
        op.f("ix_content_scripts_creator_id"),
        table_name="content_scripts",
    )
    op.drop_index(
        op.f("ix_content_scripts_calendar_item_id"),
        table_name="content_scripts",
    )
    op.drop_table("content_scripts")
