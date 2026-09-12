"""multi platform and split identity

Decouples login identity from data-provider connections and generalises
platform-specific identifiers.

* ``users`` gains ``auth_provider`` / ``auth_provider_id`` (login identity).
* ``social_accounts`` becomes one row per (user, provider) data connection.
* ``channels`` / ``videos`` / ``comments`` gain a ``platform`` discriminator and
  their ``youtube_*_id`` columns are renamed to ``external_id``.

Revision ID: b7e2a91f4c05
Revises: aa11cc22dd33
Create Date: 2026-09-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2a91f4c05'
down_revision: Union[str, Sequence[str], None] = 'aa11cc22dd33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- users: login identity -------------------------------------------------
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), nullable=False, server_default='google'))
    op.add_column('users', sa.Column('auth_provider_id', sa.String(length=255), nullable=True))
    op.create_index('ix_users_auth_provider_id', 'users', ['auth_provider_id'], unique=True)

    # --- social_accounts: one connection per (user, provider) ------------------
    op.drop_constraint('social_accounts_user_id_key', 'social_accounts', type_='unique')
    op.drop_constraint('social_accounts_provider_user_id_key', 'social_accounts', type_='unique')
    op.create_unique_constraint('uq_social_accounts_user_provider', 'social_accounts', ['user_id', 'provider'])
    op.create_unique_constraint('uq_social_accounts_provider_user', 'social_accounts', ['provider', 'provider_user_id'])
    op.create_index('ix_social_accounts_provider_user_id', 'social_accounts', ['provider_user_id'], unique=False)
    op.add_column('social_accounts', sa.Column('refresh_token_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill: existing rows hold YouTube-scoped Google tokens, so the old
    # provider_user_id (Google `sub`) is exactly the login identity id.
    op.execute(
        "UPDATE users u SET auth_provider_id = s.provider_user_id "
        "FROM social_accounts s WHERE s.user_id = u.id"
    )
    op.execute("UPDATE social_accounts SET provider = 'youtube' WHERE provider = 'google'")

    # --- channels --------------------------------------------------------------
    op.drop_index('ix_channels_youtube_channel_id', table_name='channels')
    op.alter_column('channels', 'youtube_channel_id', new_column_name='external_id')
    op.add_column('channels', sa.Column('platform', sa.String(length=50), nullable=False, server_default='youtube'))
    op.create_unique_constraint('uq_channels_platform_external_id', 'channels', ['platform', 'external_id'])
    op.create_index('ix_channels_external_id', 'channels', ['external_id'], unique=False)

    # --- videos ----------------------------------------------------------------
    op.drop_index('ix_videos_youtube_video_id', table_name='videos')
    op.alter_column('videos', 'youtube_video_id', new_column_name='external_id')
    op.add_column('videos', sa.Column('platform', sa.String(length=50), nullable=False, server_default='youtube'))
    op.create_unique_constraint('uq_videos_platform_external_id', 'videos', ['platform', 'external_id'])
    op.create_index('ix_videos_external_id', 'videos', ['external_id'], unique=False)

    # --- comments --------------------------------------------------------------
    op.drop_index('ix_comments_youtube_comment_id', table_name='comments')
    op.alter_column('comments', 'youtube_comment_id', new_column_name='external_id')
    op.create_index('ix_comments_external_id', 'comments', ['external_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema.

    Note: restoring the old global UNIQUE constraints on ``social_accounts``
    requires at most one connection per user; if any user has more than one
    data provider connected the downgrade will fail.
    """
    # --- comments --------------------------------------------------------------
    op.drop_index('ix_comments_external_id', table_name='comments')
    op.alter_column('comments', 'external_id', new_column_name='youtube_comment_id')
    op.create_index('ix_comments_youtube_comment_id', 'comments', ['youtube_comment_id'], unique=True)

    # --- videos ----------------------------------------------------------------
    op.drop_index('ix_videos_external_id', table_name='videos')
    op.drop_constraint('uq_videos_platform_external_id', 'videos', type_='unique')
    op.drop_column('videos', 'platform')
    op.alter_column('videos', 'external_id', new_column_name='youtube_video_id')
    op.create_index('ix_videos_youtube_video_id', 'videos', ['youtube_video_id'], unique=True)

    # --- channels --------------------------------------------------------------
    op.drop_index('ix_channels_external_id', table_name='channels')
    op.drop_constraint('uq_channels_platform_external_id', 'channels', type_='unique')
    op.drop_column('channels', 'platform')
    op.alter_column('channels', 'external_id', new_column_name='youtube_channel_id')
    op.create_index('ix_channels_youtube_channel_id', 'channels', ['youtube_channel_id'], unique=True)

    # --- social_accounts -------------------------------------------------------
    op.execute("UPDATE social_accounts SET provider = 'google' WHERE provider = 'youtube'")
    op.drop_column('social_accounts', 'refresh_token_expires_at')
    op.drop_index('ix_social_accounts_provider_user_id', table_name='social_accounts')
    op.drop_constraint('uq_social_accounts_provider_user', 'social_accounts', type_='unique')
    op.drop_constraint('uq_social_accounts_user_provider', 'social_accounts', type_='unique')
    op.create_unique_constraint('social_accounts_user_id_key', 'social_accounts', ['user_id'])
    op.create_unique_constraint('social_accounts_provider_user_id_key', 'social_accounts', ['provider_user_id'])

    # --- users -----------------------------------------------------------------
    op.drop_index('ix_users_auth_provider_id', table_name='users')
    op.drop_column('users', 'auth_provider_id')
    op.drop_column('users', 'auth_provider')
