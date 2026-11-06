import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, exists
from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.modules.analysis.models import Analysis
from app.modules.youtube.models import Channel, Video
from app.modules.youtube.services import sync_youtube_data

router = APIRouter(prefix="/youtube", tags=["YouTube"])
videos_router = APIRouter(prefix="/videos", tags=["Videos"])

@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="Sync YouTube Channel and Videos"
)
async def sync_videos(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Imports or updates the creator's latest YouTube channel stats and up to 50 uploaded videos."""
    try:
        videos_imported = await sync_youtube_data(db, current_user, max_results=limit)
        return {"videos_imported": videos_imported}
    except ValueError as e:
        if str(e) == "ACCOUNT_NOT_CONNECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ACCOUNT_NOT_CONNECTED",
                    "message": "No connected YouTube account found. Please link your Google profile."
                }
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@videos_router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get creator videos list with filtering and pagination"
)
async def get_videos_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    sort: str = "published_at",
    status_filter: str | None = Query(None, alias="status"),
    platform: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves a paginated list of videos synced for the authenticated creator, supporting search and sorting filters."""
    try:
        # Base query to retrieve videos owned by current creator
        base_query = select(Video).join(Channel).where(Channel.creator_id == current_user.id)

        # Apply platform filter
        if platform:
            base_query = base_query.where(Video.platform == platform)

        # Apply case-insensitive substring search filter
        if search:
            base_query = base_query.where(
                or_(
                    Video.title.ilike(f"%{search}%"),
                    Video.description.ilike(f"%{search}%")
                )
            )

        # "Analyzed" is derived from the latest Analysis run, not from comment
        # sync state. A video with comments synced but no completed analysis is
        # still pending from the creator's point of view.
        analyzed_exists = exists().where(
            Analysis.video_id == Video.id,
            Analysis.status == "completed",
        )
        if status_filter:
            if status_filter == "analyzed":
                base_query = base_query.where(analyzed_exists)
            elif status_filter == "pending":
                base_query = base_query.where(~analyzed_exists)

        # Get total count matching query criteria
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()

        # Apply sorting orders
        if sort == "views":
            base_query = base_query.order_by(Video.view_count.desc())
        elif sort == "comments":
            base_query = base_query.order_by(Video.comment_count.desc())
        elif sort == "title":
            base_query = base_query.order_by(Video.title.asc())
        else:
            # Default order: published_at DESC (newest uploads first)
            base_query = base_query.order_by(Video.published_at.desc())

        # Apply offsets and limits pagination bounds
        offset = (page - 1) * limit
        base_query = base_query.limit(limit).offset(offset)

        # Execute query
        result = await db.execute(base_query)
        videos = result.scalars().all()

        # Latest analysis run per video, newest first so the first row wins.
        latest_analysis: dict[uuid.UUID, str] = {}
        video_ids = [v.id for v in videos]
        if video_ids:
            analysis_rows = await db.execute(
                select(Analysis.video_id, Analysis.status)
                .where(Analysis.video_id.in_(video_ids))
                .order_by(Analysis.created_at.desc())
            )
            for video_id, analysis_status in analysis_rows:
                latest_analysis.setdefault(video_id, analysis_status)

        # Serialize results to match JSON contract response layout
        video_list = []
        for v in videos:
            video_list.append({
                "id": str(v.id),
                "platform": v.platform,
                "external_id": v.external_id,
                "title": v.title,
                "description": v.description,
                "thumbnail_url": v.thumbnail_url,
                "published_at": v.published_at.isoformat() if v.published_at else None,
                "view_count": v.view_count,
                "like_count": v.like_count,
                "comment_count": v.comment_count,
                "sync_status": v.sync_status,
                "analysis_status": latest_analysis.get(v.id),
                "last_synced_at": v.last_synced_at.isoformat() if v.last_synced_at else None
            })

        pages = (total_count + limit - 1) // limit if total_count > 0 else 0

        return {
            "data": video_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": pages
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@videos_router.get("/{video_id}", status_code=status.HTTP_200_OK)
async def get_video_details(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves single video details owned by the creator."""
    video_stmt = (
        select(Video)
        .join(Channel)
        .where(Video.id == video_id, Channel.creator_id == current_user.id)
    )
    video_result = await db.execute(video_stmt)
    video = video_result.scalars().first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VIDEO_NOT_FOUND",
                "message": "The requested video does not exist or you do not have permission to view it."
            }
        )

    latest_analysis_status = (
        await db.execute(
            select(Analysis.status)
            .where(Analysis.video_id == video.id)
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "id": str(video.id),
        "platform": video.platform,
        "external_id": video.external_id,
        "title": video.title,
        "description": video.description,
        "thumbnail_url": video.thumbnail_url,
        "published_at": video.published_at.isoformat() if video.published_at else None,
        "view_count": video.view_count,
        "like_count": video.like_count,
        "comment_count": video.comment_count,
        "sync_status": video.sync_status,
        "analysis_status": latest_analysis_status,
        "last_synced_at": video.last_synced_at.isoformat() if video.last_synced_at else None
    }

