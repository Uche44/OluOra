import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video
from app.integrations import google, youtube

logger = logging.getLogger(__name__)

async def get_or_refresh_google_token(db: AsyncSession, social: SocialAccount) -> str:
    """Check if the Google access token has expired (or is close to expiring) and refresh it if needed."""
    now = datetime.now(timezone.utc)
    # Refresh if token has expired or is expiring in less than 5 minutes
    if social.token_expires_at - now < timedelta(minutes=5):
        logger.info(f"Google access token for user {social.user_id} is expiring. Refreshing...")
        
        if not social.refresh_token:
            raise Exception("Google refresh token is missing. Please reconnect your YouTube account.")
            
        try:
            refresh_data = await google.refresh_google_access_token(social.refresh_token)
            new_access_token = refresh_data.get("access_token")
            expires_in = refresh_data.get("expires_in", 3600)
            
            if not new_access_token:
                raise Exception("Did not receive a new access token from Google")
                
            social.access_token = new_access_token
            social.token_expires_at = now + timedelta(seconds=expires_in)
            db.add(social)
            await db.commit()
            logger.info(f"Google access token refreshed successfully for user {social.user_id}")
        except Exception as e:
            logger.error(f"Failed to refresh Google token: {e}")
            raise Exception(f"Failed to refresh YouTube connection: {str(e)}")
            
    return social.access_token

async def sync_youtube_data(db: AsyncSession, user: User, max_results: int = 50) -> int:
    """Sync the creator's YouTube Channel details and latest uploaded videos from the YouTube API."""
    # 1. Fetch connected SocialAccount details
    social_query = select(SocialAccount).where(SocialAccount.user_id == user.id)
    social_result = await db.execute(social_query)
    social = social_result.scalar_one_or_none()
    
    if not social:
        raise ValueError("ACCOUNT_NOT_CONNECTED")
        
    # 2. Get valid access token
    access_token = await get_or_refresh_google_token(db, social)
    
    # 3. Fetch Channel Metadata from YouTube API
    channel_data = await youtube.fetch_channel_details(access_token)
    
    youtube_channel_id = channel_data["id"]
    snippet = channel_data.get("snippet", {})
    stats = channel_data.get("statistics", {})
    content_details = channel_data.get("contentDetails", {})
    
    title = snippet.get("title", "My YouTube Channel")
    description = snippet.get("description", "")
    thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url")
    subscriber_count = int(stats.get("subscriberCount", 0))
    video_count = int(stats.get("videoCount", 0))
    
    uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        # Fail-safe: replace UC with UU in channel ID to builduploads playlist
        uploads_playlist_id = "UU" + youtube_channel_id[2:] if youtube_channel_id.startswith("UC") else None
        
    if not uploads_playlist_id:
        raise Exception("Failed to locate uploads playlist ID for YouTube Channel")
        
    # Save/Update Channel in Database
    channel_query = select(Channel).where(Channel.youtube_channel_id == youtube_channel_id)
    channel_db_result = await db.execute(channel_query)
    channel = channel_db_result.scalar_one_or_none()
    
    if not channel:
        channel = Channel(
            creator_id=user.id,
            youtube_channel_id=youtube_channel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            subscriber_count=subscriber_count,
            video_count=video_count
        )
        db.add(channel)
    else:
        channel.title = title
        channel.description = description
        channel.thumbnail_url = thumbnail_url
        channel.subscriber_count = subscriber_count
        channel.video_count = video_count
        db.add(channel)
        
    await db.commit()
    await db.refresh(channel)
    
    # 4. Fetch Latest Video IDs from Uploads Playlist
    video_ids = await youtube.fetch_latest_videos(access_token, uploads_playlist_id, max_results)
    if not video_ids:
        return 0
        
    # 5. Fetch Full Video Metadata in Batches
    videos_data = await youtube.fetch_videos_metadata(access_token, video_ids)
    
    videos_synced = 0
    for v_data in videos_data:
        v_id = v_data["id"]
        v_snippet = v_data.get("snippet", {})
        v_stats = v_data.get("statistics", {})
        
        v_title = v_snippet.get("title", "Untitled Video")
        v_desc = v_snippet.get("description", "")
        v_thumb = v_snippet.get("thumbnails", {}).get("high", {}).get("url") or v_snippet.get("thumbnails", {}).get("default", {}).get("url")
        
        published_at_str = v_snippet.get("publishedAt")
        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00")) if published_at_str else datetime.now(timezone.utc)
        
        views = int(v_stats.get("viewCount", 0))
        likes = int(v_stats.get("likeCount", 0))
        comments = int(v_stats.get("commentCount", 0))
        
        # Save/Update Video in Database
        video_query = select(Video).where(Video.youtube_video_id == v_id)
        video_db_result = await db.execute(video_query)
        video = video_db_result.scalar_one_or_none()
        
        if not video:
            video = Video(
                channel_id=channel.id,
                youtube_video_id=v_id,
                title=v_title,
                description=v_desc,
                thumbnail_url=v_thumb,
                published_at=published_at,
                view_count=views,
                like_count=likes,
                comment_count=comments,
                sync_status="pending"
            )
            db.add(video)
        else:
            video.title = v_title
            video.description = v_desc
            video.thumbnail_url = v_thumb
            video.view_count = views
            video.like_count = likes
            video.comment_count = comments
            db.add(video)
            
        videos_synced += 1
        
    await db.commit()
    return videos_synced
