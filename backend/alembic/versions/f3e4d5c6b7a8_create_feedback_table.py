"""create_feedback_table

Revision ID: f3e4d5c6b7a8
Revises: e8f1a2b3c4d5
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3e4d5c6b7a8'
down_revision: Union[str, Sequence[str], None] = 'e8f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'feedback',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('page', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_user_id'), 'feedback', ['user_id'], unique=False)
    op.create_index(op.f('ix_feedback_status'), 'feedback', ['status'], unique=False)
    op.create_index(op.f('ix_feedback_created_at'), 'feedback', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_feedback_created_at'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_status'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_user_id'), table_name='feedback')
    op.drop_table('feedback')
