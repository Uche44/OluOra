"""add video transcripts and calendar content context

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-05 06:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("transcript", sa.Text(), nullable=True))
    op.add_column(
        "videos",
        sa.Column("transcript_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "content_calendar_items",
        sa.Column("content_context", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE content_calendar_items SET content_context = '' "
        "WHERE content_context IS NULL"
    )
    op.alter_column(
        "content_calendar_items", "content_context", nullable=False
    )


def downgrade() -> None:
    op.drop_column("content_calendar_items", "content_context")
    op.drop_column("videos", "transcript_fetched_at")
    op.drop_column("videos", "transcript")
