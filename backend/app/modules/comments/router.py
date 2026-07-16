import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.comments.schemas import CommentPaginationResponse
from app.modules.comments.services import sync_comments_for_video
from app.modules.youtube.services import get_or_refresh_google_token

router = APIRouter(prefix="/videos", tags=["Comments"])

@router.get(
    "/{video_id}/comments",
    response_model=CommentPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get comments for a video"
)
async def get_video_comments(
    video_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves a paginated list of comments for a video owned by the authenticated creator."""
    # 1. Verify video existence and user ownership
    video_stmt = (
        select(Video)
        .join(Channel)
        .where(Video.id == video_id, Channel.creator_id == current_user.id)
    )
    video_result = await db.execute(video_stmt)
    video = video_result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VIDEO_NOT_FOUND",
                "message": "The requested video does not exist or you do not have permission to view it."
            }
        )
        
    # 2. Build comment retrieval query
    comments_stmt = (
        select(Comment)
        .where(Comment.video_id == video_id)
        .order_by(Comment.published_at.desc())
    )
    
    # 3. Get total count
    count_stmt = select(func.count()).select_from(comments_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar_one()
    
    # 4. Paginate results
    offset = (page - 1) * limit
    comments_stmt = comments_stmt.limit(limit).offset(offset)
    comments_result = await db.execute(comments_stmt)
    comments = comments_result.scalars().all()
    
    pages = (total_count + limit - 1) // limit if total_count > 0 else 0
    
    return {
        "data": comments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": pages
        }
    }

@router.post(
    "/{video_id}/comments/sync",
    status_code=status.HTTP_200_OK,
    summary="Manually trigger comments synchronization"
)
async def sync_comments(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetches and updates comments for a specific video from YouTube."""
    # 1. Verify video existence and user ownership
    video_stmt = (
        select(Video)
        .join(Channel)
        .where(Video.id == video_id, Channel.creator_id == current_user.id)
    )
    video_result = await db.execute(video_stmt)
    video = video_result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VIDEO_NOT_FOUND",
                "message": "The requested video does not exist or you do not have permission to sync it."
            }
        )
        
    # 2. Fetch connected Google SocialAccount details
    social_stmt = select(SocialAccount).where(SocialAccount.user_id == current_user.id)
    social_result = await db.execute(social_stmt)
    social = social_result.scalar_one_or_none()
    
    if not social:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ACCOUNT_NOT_CONNECTED",
                "message": "No connected YouTube account found. Please link your Google profile."
            }
        )
        
    # 3. Synchronize comments
    try:
        access_token = await get_or_refresh_google_token(db, social)
        new_comments_count = await sync_comments_for_video(db, video, access_token)
        return {
            "success": True,
            "message": f"Successfully synced comments. {new_comments_count} new comments added.",
            "data": {
                "synced_count": new_comments_count,
                "sync_status": video.sync_status
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SYNC_FAILED",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SYNC_ERROR",
                "message": f"An error occurred while syncing: {str(e)}"
            }
        )
