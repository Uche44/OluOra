import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.integrations import tiktok
from app.modules.users.models import User
from app.modules.users.quota import log_api_quota
from app.modules.users.social_tokens import get_social_account, get_or_refresh_social_token
from app.modules.youtube.models import Channel, Video

logger = logging.getLogger(__name__)


def _parse_create_time(value) -> datetime:
    """TikTok ``create_time`` is a UTC unix epoch in seconds."""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


async def sync_tiktok_data(db: AsyncSession, user: User, max_videos: int = 50) -> int:
    """Sync the creator's TikTok profile and public video catalog via the Display API.

    The Display API exposes no comment-read endpoint, so only channel and video
    metadata are imported here. Comments are ingested separately through the
    third-party provider in ``app.integrations.scrapecreators``.
    """
    # 1. Fetch connected TikTok account
    social = await get_social_account(db, user.id, providers.TIKTOK)
    if not social:
        raise ValueError("ACCOUNT_NOT_CONNECTED")

    access_token = await get_or_refresh_social_token(db, social)

    # 2. Upsert the channel from the user profile
    user_info = await tiktok.fetch_user_info(access_token)
    await log_api_quota(db, user.id, "tiktok.user.info", 1)

    open_id = user_info.get("open_id") or social.provider_user_id
    title = user_info.get("display_name") or user_info.get("username") or "My TikTok Account"

    channel_query = select(Channel).where(
        Channel.platform == providers.TIKTOK,
        Channel.external_id == open_id,
    )
    channel_result = await db.execute(channel_query)
    channel = channel_result.scalar_one_or_none()

    if not channel:
        channel = Channel(
            creator_id=user.id,
            platform=providers.TIKTOK,
            external_id=open_id,
            title=title,
        )
        db.add(channel)
    else:
        channel.title = title

    channel.description = user_info.get("bio_description")
    channel.thumbnail_url = user_info.get("avatar_large_url") or user_info.get("avatar_url")
    # Some scopes (user.info.stats) may not be granted; default to 0 rather than failing.
    channel.subscriber_count = int(user_info.get("follower_count") or 0)
    channel.video_count = int(user_info.get("video_count") or 0)
    db.add(channel)

    await db.commit()
    await db.refresh(channel)

    # 3. Page through the public video catalog
    videos_synced = 0
    cursor = None
    while videos_synced < max_videos:
        page = await tiktok.fetch_user_videos(
            access_token,
            cursor=cursor,
            max_count=min(20, max_videos - videos_synced),
        )
        await log_api_quota(db, user.id, "tiktok.video.list", 1)

        videos = page.get("videos") or []
        if not videos:
            break

        for item in videos:
            video_id = item.get("id")
            if not video_id:
                continue

            video_query = select(Video).where(
                Video.platform == providers.TIKTOK,
                Video.external_id == video_id,
            )
            video_result = await db.execute(video_query)
            video = video_result.scalar_one_or_none()

            description = item.get("video_description") or ""
            title_value = item.get("title") or description or "Untitled Video"

            if not video:
                video = Video(
                    channel_id=channel.id,
                    platform=providers.TIKTOK,
                    external_id=video_id,
                )
                db.add(video)

            video.title = title_value[:255]
            video.description = description
            video.thumbnail_url = item.get("cover_image_url")
            # Kept so comment ingestion can address the video by URL. Only
            # overwritten when TikTok returns one, so re-syncs cannot erase it.
            share_url = item.get("share_url")
            if share_url:
                video.url = share_url
            video.published_at = _parse_create_time(item.get("create_time"))
            video.view_count = int(item.get("view_count") or 0)
            video.like_count = int(item.get("like_count") or 0)
            video.comment_count = int(item.get("comment_count") or 0)
            videos_synced += 1

        if not page.get("has_more"):
            break
        cursor = page.get("cursor")
        if not cursor:
            break

    await db.commit()
    return videos_synced
