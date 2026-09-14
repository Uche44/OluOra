"""add_video_url

Adds a canonical public URL to videos so third-party enrichment providers can
address a video (TikTok comments are fetched by video URL).

Revision ID: c4f1a7b9e2d3
Revises: b7e2a91f4c05
Create Date: 2026-09-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a7b9e2d3'
down_revision: Union[str, Sequence[str], None] = 'b7e2a91f4c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('videos', sa.Column('url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('videos', 'url')
