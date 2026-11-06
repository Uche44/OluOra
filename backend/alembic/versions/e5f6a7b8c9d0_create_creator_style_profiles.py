"""create creator style profiles

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-05 04:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "creator_style_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tone", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=100), nullable=False),
        sa.Column("audience_description", sa.Text(), nullable=False),
        sa.Column("technical_depth", sa.String(length=50), nullable=False),
        sa.Column("preferred_structures", sa.JSON(), nullable=False),
        sa.Column("avoid", sa.JSON(), nullable=False),
        sa.Column("posting_cadence", sa.Integer(), nullable=False),
        sa.Column("preferred_formats", sa.JSON(), nullable=False),
        sa.Column("preferred_platforms", sa.JSON(), nullable=False),
        sa.Column("reference_notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_creator_style_profiles_user"),
    )


def downgrade() -> None:
    op.drop_table("creator_style_profiles")
