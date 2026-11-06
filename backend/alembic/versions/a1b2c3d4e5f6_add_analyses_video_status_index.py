"""add analyses video_id/status index

Revision ID: a1b2c3d4e5f6
Revises: f9e0a1b2c3d4
Create Date: 2026-11-05 00:30:00.000000

``GET /videos?status=analyzed``, the ``pending`` complement, and the dashboard's
``videos_analyzed`` count all filter analyses by ``(video_id, status)``. Without
an index each video in a page triggers a sequential scan of ``analyses``.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f9e0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_analyses_video_id_status",
        "analyses",
        ["video_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_analyses_video_id_status", table_name="analyses")
