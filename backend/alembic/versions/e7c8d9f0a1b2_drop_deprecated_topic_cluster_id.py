"""drop deprecated comments.topic_cluster_id

Revision ID: e7c8d9f0a1b2
Revises: d6a7b8c9e0f1
Create Date: 2026-11-05 00:10:00.000000

Membership now lives in ``comment_cluster_memberships``, scoped per analysis
run. ``comments.topic_cluster_id`` was kept for one deploy so the backfill could
be verified; it is no longer read or written, so drop it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7c8d9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "d6a7b8c9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "comments_topic_cluster_id_fkey", "comments", type_="foreignkey"
    )
    op.drop_column("comments", "topic_cluster_id")


def downgrade() -> None:
    op.add_column("comments", sa.Column("topic_cluster_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "comments_topic_cluster_id_fkey",
        "comments",
        "topic_clusters",
        ["topic_cluster_id"],
        ["id"],
        ondelete="SET NULL",
    )
