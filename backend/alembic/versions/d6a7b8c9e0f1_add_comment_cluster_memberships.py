"""add comment cluster memberships

Revision ID: d6a7b8c9e0f1
Revises: b9c1d2e3f4a5
Create Date: 2026-11-05 00:00:00.000000

Membership used to live in ``comments.topic_cluster_id``, a single mutable FK
that every re-analysis overwrote. This migration introduces a per-run join table
so each analysis keeps its own immutable cluster membership.

The legacy column is intentionally left in place (deprecated, no longer written)
so the migration is non-destructive; it can be dropped in a follow-up revision.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6a7b8c9e0f1"
down_revision: Union[str, Sequence[str], None] = "b9c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comment_cluster_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("cluster_id", sa.UUID(), nullable=False),
        sa.Column("comment_id", sa.UUID(), nullable=False),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["topic_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "comment_id", name="uq_ccm_analysis_comment"),
    )
    op.create_index(
        op.f("ix_comment_cluster_memberships_analysis_id"),
        "comment_cluster_memberships",
        ["analysis_id"],
    )
    op.create_index(
        op.f("ix_comment_cluster_memberships_cluster_id"),
        "comment_cluster_memberships",
        ["cluster_id"],
    )
    op.create_index(
        op.f("ix_comment_cluster_memberships_comment_id"),
        "comment_cluster_memberships",
        ["comment_id"],
    )
    op.create_index(
        "ix_ccm_analysis_cluster",
        "comment_cluster_memberships",
        ["analysis_id", "cluster_id"],
    )

    # Backfill the latest known membership. Older runs were already overwritten
    # by the previous model and cannot be reconstructed.
    op.execute(
        """
        INSERT INTO comment_cluster_memberships
            (id, analysis_id, cluster_id, comment_id, distance, created_at)
        SELECT gen_random_uuid(), tc.analysis_id, c.topic_cluster_id, c.id, NULL, NOW()
        FROM comments c
        JOIN topic_clusters tc ON tc.id = c.topic_cluster_id
        WHERE c.topic_cluster_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ccm_analysis_cluster", table_name="comment_cluster_memberships")
    op.drop_index(
        op.f("ix_comment_cluster_memberships_comment_id"),
        table_name="comment_cluster_memberships",
    )
    op.drop_index(
        op.f("ix_comment_cluster_memberships_cluster_id"),
        table_name="comment_cluster_memberships",
    )
    op.drop_index(
        op.f("ix_comment_cluster_memberships_analysis_id"),
        table_name="comment_cluster_memberships",
    )
    op.drop_table("comment_cluster_memberships")
