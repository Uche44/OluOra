"""add analysis editorial summary

Revision ID: c2d3e4f5a6b7
Revises: b8c9d0e1f2a3
Create Date: 2026-11-11 00:00:00.000000

Each immutable analysis run now stores the LLM-written overall summary shown in
the "Audience AI Summary" card. The column is nullable so existing runs keep
working; the UI falls back to a local heuristic until a video is analyzed again.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "summary")
