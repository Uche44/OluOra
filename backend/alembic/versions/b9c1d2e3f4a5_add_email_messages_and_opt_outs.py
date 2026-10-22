"""add_email_messages_and_opt_outs

Revision ID: b9c1d2e3f4a5
Revises: f3e4d5c6b7a8
Create Date: 2026-10-22 00:00:00.000000

Adds the outbound-email log/batch tables plus the opt-out columns that back
one-click unsubscribe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'f3e4d5c6b7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'email_batches',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('requested_by', sa.Uuid(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('sent', sa.Integer(), nullable=False),
        sa.Column('failed', sa.Integer(), nullable=False),
        sa.Column('skipped', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_batches_category'), 'email_batches', ['category'], unique=False)
    op.create_index(op.f('ix_email_batches_status'), 'email_batches', ['status'], unique=False)

    op.create_table(
        'email_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('to_email', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('batch_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['batch_id'], ['email_batches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_messages_to_email'), 'email_messages', ['to_email'], unique=False)
    op.create_index(op.f('ix_email_messages_user_id'), 'email_messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_email_messages_category'), 'email_messages', ['category'], unique=False)
    op.create_index(op.f('ix_email_messages_status'), 'email_messages', ['status'], unique=False)
    op.create_index(op.f('ix_email_messages_batch_id'), 'email_messages', ['batch_id'], unique=False)
    op.create_index(op.f('ix_email_messages_created_at'), 'email_messages', ['created_at'], unique=False)

    op.add_column(
        'waitlist_entries',
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('email_opt_out_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'email_opt_out_at')
    op.drop_column('waitlist_entries', 'unsubscribed_at')

    op.drop_index(op.f('ix_email_messages_created_at'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_batch_id'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_status'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_category'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_user_id'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_to_email'), table_name='email_messages')
    op.drop_table('email_messages')

    op.drop_index(op.f('ix_email_batches_status'), table_name='email_batches')
    op.drop_index(op.f('ix_email_batches_category'), table_name='email_batches')
    op.drop_table('email_batches')
