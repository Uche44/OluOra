"""rename comment sync status completed -> synced

Revision ID: f9e0a1b2c3d4
Revises: e7c8d9f0a1b2
Create Date: 2026-11-05 00:20:00.000000

``videos.sync_status`` only tracks comment ingestion. It previously used
``completed``, which the UI and analytics confused with "analysis complete".
Rename the sync state to ``synced`` so "analyzed" can be derived exclusively
from ``analyses.status``.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f9e0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "e7c8d9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE videos SET sync_status = 'synced' WHERE sync_status = 'completed'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE videos SET sync_status = 'completed' WHERE sync_status = 'synced'"
    )
