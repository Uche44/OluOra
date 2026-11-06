"""create content calendar items

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-05 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_calendar_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("angle", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("length", sa.String(length=50), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["content_opportunities.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_calendar_items_creator_id"),
        "content_calendar_items",
        ["creator_id"],
    )
    op.create_index(
        op.f("ix_content_calendar_items_opportunity_id"),
        "content_calendar_items",
        ["opportunity_id"],
    )
    op.create_index(
        op.f("ix_content_calendar_items_scheduled_date"),
        "content_calendar_items",
        ["scheduled_date"],
    )
    op.create_index(
        "ix_content_calendar_items_creator_date",
        "content_calendar_items",
        ["creator_id", "scheduled_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_calendar_items_creator_date",
        table_name="content_calendar_items",
    )
    op.drop_index(
        op.f("ix_content_calendar_items_scheduled_date"),
        table_name="content_calendar_items",
    )
    op.drop_index(
        op.f("ix_content_calendar_items_opportunity_id"),
        table_name="content_calendar_items",
    )
    op.drop_index(
        op.f("ix_content_calendar_items_creator_id"),
        table_name="content_calendar_items",
    )
    op.drop_table("content_calendar_items")
