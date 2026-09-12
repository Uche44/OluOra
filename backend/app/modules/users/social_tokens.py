"""Provider-agnostic helpers for connected social accounts."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.integrations import google, tiktok
from app.modules.users.models import SocialAccount

logger = logging.getLogger(__name__)

# Refresh a token when it is within this window of expiring.
REFRESH_MARGIN = timedelta(minutes=5)


async def get_social_account(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> SocialAccount | None:
    """Return the user's connection for ``provider``, if any."""
    stmt = select(SocialAccount).where(
        SocialAccount.user_id == user_id,
        SocialAccount.provider == provider,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_refresh_social_token(db: AsyncSession, social: SocialAccount) -> str:
    """Return a valid access token for a connected account, refreshing it when close to expiry."""
    now = datetime.now(timezone.utc)
    if social.token_expires_at - now >= REFRESH_MARGIN:
        return social.access_token

    if not social.refresh_token:
        raise Exception(
            f"{social.provider} refresh token is missing. Please reconnect your {social.provider} account."
        )

    logger.info(f"Refreshing {social.provider} access token for user {social.user_id}")
    if social.provider == providers.TIKTOK:
        refresh_data = await tiktok.refresh_access_token(social.refresh_token)
    elif social.provider == providers.YOUTUBE:
        refresh_data = await google.refresh_google_access_token(social.refresh_token)
    else:
        raise Exception(f"Token refresh is not supported for provider '{social.provider}'")

    new_access_token = refresh_data.get("access_token")
    if not new_access_token:
        raise Exception(f"Did not receive a new access token from {social.provider}")

    social.access_token = new_access_token
    social.token_expires_at = now + timedelta(seconds=refresh_data.get("expires_in", 3600))
    # TikTok rotates refresh tokens (the returned value may differ from the sent one).
    if refresh_data.get("refresh_token"):
        social.refresh_token = refresh_data["refresh_token"]
    if refresh_data.get("refresh_expires_in"):
        social.refresh_token_expires_at = now + timedelta(
            seconds=refresh_data["refresh_expires_in"]
        )

    db.add(social)
    await db.commit()
    return social.access_token
