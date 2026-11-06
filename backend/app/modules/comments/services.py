import logging
from datetime import datetime, timezone
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.youtube.models import Video, Channel
from app.modules.comments.models import Comment
from app.integrations import scrapecreators, youtube
from app.modules.users.quota import verify_quota_limit, log_api_quota

logger = logging.getLogger(__name__)

async def sync_comments_for_video(db: AsyncSession, video: Video, access_token: str, max_comments_limit: int = 500) -> int:
    """
    Sync comments for a given video from YouTube API.
    Implements incremental delta sync: stops when hitting a comment older than the newest stored comment.
    """
    # Get creator user ID to check quota
    creator_query = select(Channel.creator_id).where(Channel.id == video.channel_id)
    creator_res = await db.execute(creator_query)
    user_id = creator_res.scalar_one()

    # 1. Find the newest comment's published_at currently in the database
    latest_stmt = (
        select(Comment.published_at)
        .where(Comment.video_id == video.id)
        .order_by(desc(Comment.published_at))
        .limit(1)
    )
    latest_result = await db.execute(latest_stmt)
    latest_published_at = latest_result.scalar_one_or_none()
    
    # Ensure latest_published_at is timezone-aware
    if latest_published_at and latest_published_at.tzinfo is None:
        latest_published_at = latest_published_at.replace(tzinfo=timezone.utc)
        
    logger.info(f"Syncing comments for video {video.external_id}. Latest stored comment: {latest_published_at}")
    
    new_comments_count = 0
    page_token = None
    stop_sync = False
    total_fetched = 0
    
    while not stop_sync and total_fetched < max_comments_limit:
        # Check quota limit before making the request
        await verify_quota_limit(db, user_id, planned_cost=1)

        # Fetch a page of comment threads
        try:
            req_etag = video.etag if page_token is None else None
            response_data = await youtube.fetch_comment_threads(
                access_token=access_token,
                video_id=video.external_id,
                max_results=100,
                page_token=page_token,
                etag=req_etag
            )
            
            # If ETag matched (HTTP 304)
            if response_data.get("etag_matched"):
                logger.info(f"ETag matched for video {video.external_id}. Comments unchanged.")
                video.last_synced_at = datetime.now(timezone.utc)
                video.sync_status = "synced"
                db.add(video)
                await db.commit()
                return 0

            # Store the new ETag on the first page load
            if page_token is None:
                new_etag = response_data.get("_etag")
                if new_etag:
                    video.etag = new_etag
                    db.add(video)

                await log_api_quota(db, user_id, "commentThreads.list", 1)
        except Exception as e:
            if str(e) == "COMMENTS_DISABLED":
                video.sync_status = "disabled"
                video.last_synced_at = datetime.now(timezone.utc)
                db.add(video)
                await db.commit()
                logger.warning(f"Comments are disabled for video {video.external_id}")
                return 0
            logger.error(f"Failed to fetch comment threads: {e}")
            raise
            
        items = response_data.get("items", [])
        if not items:
            break
            
        for item in items:
            snippet = item.get("snippet", {})
            top_level_wrapper = snippet.get("topLevelComment", {})
            top_comment_id = top_level_wrapper.get("id")
            top_snippet = top_level_wrapper.get("snippet", {})
            
            if not top_comment_id or not top_snippet:
                continue
                
            published_at_str = top_snippet.get("publishedAt")
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00")) if published_at_str else datetime.now(timezone.utc)
            
            # Check if this comment is older than or equal to our newest stored comment
            if latest_published_at and published_at <= latest_published_at:
                logger.info(f"Reached comment older than latest sync timestamp: {published_at}. Stopping sync.")
                stop_sync = True
                break
                
            author_name = top_snippet.get("authorDisplayName", "Unknown")
            author_profile_image = top_snippet.get("authorProfileImageUrl")
            text = top_snippet.get("textDisplay", "")
            like_count = int(top_snippet.get("likeCount", 0))
            
            # Check if comment already exists (failsafe)
            exists_stmt = select(Comment).where(Comment.external_id == top_comment_id)
            exists_result = await db.execute(exists_stmt)
            comment_db = exists_result.scalar_one_or_none()
            
            if not comment_db:
                comment_db = Comment(
                    video_id=video.id,
                    external_id=top_comment_id,
                    author_name=author_name,
                    author_profile_image=author_profile_image,
                    text=text,
                    like_count=like_count,
                    published_at=published_at,
                    parent_id=None
                )
                db.add(comment_db)
                # Flush to generate UUID id for parent referencing
                await db.flush()
                new_comments_count += 1
            else:
                comment_db.like_count = like_count
                comment_db.text = text
                comment_db.author_name = author_name
                comment_db.author_profile_image = author_profile_image
                db.add(comment_db)
                
            total_fetched += 1
            
            # Process replies
            replies_container = item.get("replies", {})
            reply_items = replies_container.get("comments", [])
            for reply_item in reply_items:
                reply_id = reply_item.get("id")
                reply_snippet = reply_item.get("snippet", {})
                if not reply_id or not reply_snippet:
                    continue
                    
                r_published_at_str = reply_snippet.get("publishedAt")
                r_published_at = datetime.fromisoformat(r_published_at_str.replace("Z", "+00:00")) if r_published_at_str else datetime.now(timezone.utc)
                r_author_name = reply_snippet.get("authorDisplayName", "Unknown")
                r_author_profile_image = reply_snippet.get("authorProfileImageUrl")
                r_text = reply_snippet.get("textDisplay", "")
                r_like_count = int(reply_snippet.get("likeCount", 0))
                
                reply_exists_stmt = select(Comment).where(Comment.external_id == reply_id)
                reply_exists_result = await db.execute(reply_exists_stmt)
                reply_db = reply_exists_result.scalar_one_or_none()
                
                if not reply_db:
                    reply_db = Comment(
                        video_id=video.id,
                        external_id=reply_id,
                        author_name=r_author_name,
                        author_profile_image=r_author_profile_image,
                        text=r_text,
                        like_count=r_like_count,
                        published_at=r_published_at,
                        parent_id=comment_db.id
                    )
                    db.add(reply_db)
                    new_comments_count += 1
                else:
                    reply_db.like_count = r_like_count
                    reply_db.text = r_text
                    reply_db.author_name = r_author_name
                    reply_db.author_profile_image = r_author_profile_image
                    db.add(reply_db)
                    
        page_token = response_data.get("nextPageToken")
        if not page_token:
            break
            
    video.last_synced_at = datetime.now(timezone.utc)
    if video.sync_status != "synced":
        video.sync_status = "synced"
    db.add(video)
    await db.commit()
    
    logger.info(f"Comments sync completed. Synced {new_comments_count} comments.")
    return new_comments_count


async def sync_tiktok_comments_for_video(
    db: AsyncSession, video: Video, max_comments_limit: int = 500
) -> int:
    """Sync a TikTok video's top-level public comments via the third-party provider.

    TikTok's Display API exposes no comment-read endpoint, so comments are sourced
    from ScrapeCreators and paged by cursor. Each page is billed as one request,
    so quota is checked (and logged) per page exactly like the YouTube path.

    Only top-level comments are ingested here; replies live behind a separate
    provider endpoint and are deliberately out of scope.
    """
    if not scrapecreators.is_configured():
        raise ValueError("COMMENTS_NOT_SUPPORTED")
    if not video.url:
        # Videos imported before URL capture was added must be re-synced first.
        raise ValueError("VIDEO_URL_MISSING")

    creator_query = select(Channel.creator_id).where(Channel.id == video.channel_id)
    user_id = (await db.execute(creator_query)).scalar_one()

    new_comments_count = 0
    total_fetched = 0
    cursor = None

    while total_fetched < max_comments_limit:
        await verify_quota_limit(db, user_id, planned_cost=1)

        payload = await scrapecreators.fetch_video_comments(video.url, cursor=cursor)
        await log_api_quota(db, user_id, "scrapecreators.tiktok.comments", 1)

        page_comments = scrapecreators.normalize_comments(payload)
        if not page_comments:
            break

        for item in page_comments:
            exists_result = await db.execute(
                select(Comment).where(Comment.external_id == item.external_id)
            )
            comment_db = exists_result.scalar_one_or_none()

            if not comment_db:
                comment_db = Comment(
                    video_id=video.id,
                    external_id=item.external_id,
                    author_name=item.author_name,
                    author_profile_image=item.author_profile_image,
                    text=item.text,
                    like_count=item.like_count,
                    published_at=item.published_at,
                    parent_id=None,
                )
                db.add(comment_db)
                new_comments_count += 1
            else:
                comment_db.like_count = item.like_count
                comment_db.text = item.text
                comment_db.author_name = item.author_name
                comment_db.author_profile_image = item.author_profile_image
                db.add(comment_db)

            total_fetched += 1
            if total_fetched >= max_comments_limit:
                break

        cursor = scrapecreators.next_cursor(payload)
        if cursor is None:
            break

    video.last_synced_at = datetime.now(timezone.utc)
    video.sync_status = "synced"
    db.add(video)
    await db.commit()

    logger.info(f"TikTok comments sync completed. Synced {new_comments_count} comments.")
    return new_comments_count
