"""create content opportunities and evidence

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-05 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_opportunities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=True),
        sa.Column("source_video_id", sa.UUID(), nullable=True),
        sa.Column("source_video_title", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("suggested_format", sa.String(length=50), nullable=False),
        sa.Column("suggested_length", sa.String(length=50), nullable=False),
        sa.Column("suggested_angle", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_evidence_backed", sa.Boolean(), nullable=False),
        sa.Column("generation_hash", sa.String(length=64), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_opportunities_creator_id"),
        "content_opportunities",
        ["creator_id"],
    )
    op.create_index(
        op.f("ix_content_opportunities_analysis_id"),
        "content_opportunities",
        ["analysis_id"],
    )
    op.create_index(
        op.f("ix_content_opportunities_generation_hash"),
        "content_opportunities",
        ["generation_hash"],
    )
    op.create_index(
        "ix_content_opportunities_creator_status",
        "content_opportunities",
        ["creator_id", "status"],
    )

    op.create_table(
        "content_opportunity_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("insight_id", sa.UUID(), nullable=True),
        sa.Column("cluster_id", sa.UUID(), nullable=True),
        sa.Column("comment_id", sa.UUID(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["topic_clusters.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_opportunity_evidence_opportunity_id"),
        "content_opportunity_evidence",
        ["opportunity_id"],
    )
    op.create_index(
        op.f("ix_content_opportunity_evidence_insight_id"),
        "content_opportunity_evidence",
        ["insight_id"],
    )
    op.create_index(
        op.f("ix_content_opportunity_evidence_cluster_id"),
        "content_opportunity_evidence",
        ["cluster_id"],
    )
    op.create_index(
        op.f("ix_content_opportunity_evidence_comment_id"),
        "content_opportunity_evidence",
        ["comment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_content_opportunity_evidence_comment_id"),
        table_name="content_opportunity_evidence",
    )
    op.drop_index(
        op.f("ix_content_opportunity_evidence_cluster_id"),
        table_name="content_opportunity_evidence",
    )
    op.drop_index(
        op.f("ix_content_opportunity_evidence_insight_id"),
        table_name="content_opportunity_evidence",
    )
    op.drop_index(
        op.f("ix_content_opportunity_evidence_opportunity_id"),
        table_name="content_opportunity_evidence",
    )
    op.drop_table("content_opportunity_evidence")

    op.drop_index(
        "ix_content_opportunities_creator_status",
        table_name="content_opportunities",
    )
    op.drop_index(
        op.f("ix_content_opportunities_generation_hash"),
        table_name="content_opportunities",
    )
    op.drop_index(
        op.f("ix_content_opportunities_analysis_id"),
        table_name="content_opportunities",
    )
    op.drop_index(
        op.f("ix_content_opportunities_creator_id"),
        table_name="content_opportunities",
    )
    op.drop_table("content_opportunities")
