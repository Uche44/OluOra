import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Video, Channel
from app.modules.youtube.services import get_or_refresh_google_token
from app.modules.analysis.models import Analysis, Insight, TopicCluster
from app.modules.analysis.services import run_end_to_end_analysis
from app.modules.analysis.schemas import InsightsListResponse, InsightResponse, AnalysisResponse, TopicClusterResponse

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/{analysis_id}/insights", response_model=InsightsListResponse)
async def get_analysis_insights(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the extracted audience insights (questions, pain points, positive feedback)
    associated with a specific analysis run.
    """
    # 1. Verify analysis run exists and user owns the video
    analysis_stmt = (
        select(Analysis)
        .join(Video)
        .join(Channel)
        .where(Analysis.id == analysis_id, Channel.creator_id == current_user.id)
    )
    analysis_result = await db.execute(analysis_stmt)
    analysis = analysis_result.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "The requested analysis run does not exist or you do not have permission to view it."
            }
        )

    # 2. Fetch all insights for this analysis run
    insights_result = await db.execute(
        select(Insight).where(Insight.analysis_id == analysis_id)
    )
    insights = insights_result.scalars().all()

    # 3. Categorize insights by type
    questions = [i for i in insights if i.type == "question"]
    pain_points = [i for i in insights if i.type == "pain_point"]
    positive_themes = [i for i in insights if i.type == "positive_theme"]

    return InsightsListResponse(
        questions=questions,
        pain_points=pain_points,
        positive_themes=positive_themes
    )


@router.get("/{analysis_id}/recommendations", response_model=list[InsightResponse])
async def get_analysis_recommendations(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the extracted actionable content recommendations (video suggestions, FAQ write-ups)
    associated with a specific analysis run.
    """
    # 1. Verify analysis run exists and user owns the video
    analysis_stmt = (
        select(Analysis)
        .join(Video)
        .join(Channel)
        .where(Analysis.id == analysis_id, Channel.creator_id == current_user.id)
    )
    analysis_result = await db.execute(analysis_stmt)
    analysis = analysis_result.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "The requested analysis run does not exist or you do not have permission to view it."
            }
        )

    # 2. Fetch all recommendations for this analysis run
    insights_result = await db.execute(
        select(Insight).where(
            Insight.analysis_id == analysis_id,
            Insight.type == "recommendation"
        )
    )
    recommendations = insights_result.scalars().all()
    return recommendations


@router.post("/run/{video_id}", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_analysis(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an asynchronous comment analysis run for the specified video.
    This creates a new immutable Analysis record, pulls comments from YouTube,
    generates embeddings, groups them via KMeans, and auto-labels them.
    """
    # 1. Verify video existence and ownership
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

    # 2. Retrieve active social connection & refresh google token
    social_stmt = select(SocialAccount).where(
        SocialAccount.user_id == current_user.id,
        SocialAccount.provider == "google"
    )
    social_result = await db.execute(social_stmt)
    social = social_result.scalars().first()

    google_token = None
    if social:
        try:
            google_token = await get_or_refresh_google_token(db, social)
        except Exception as e:
            # Continue analysis even if OAuth refresh fails (will use local comments cache)
            pass

    # 3. Create a new immutable Analysis run record
    analysis = Analysis(
        video_id=video_id,
        status="pending",
        comments_analyzed=0
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # 4. Schedule end-to-end processing pipeline in the background
    background_tasks.add_task(
        run_end_to_end_analysis,
        analysis_id=analysis.id,
        video_id=video_id,
        google_token=google_token
    )

    return analysis


@router.get("/history/{video_id}", response_model=list[AnalysisResponse])
async def get_analysis_history(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists the historical runs of analysis conducted for a specific video,
    ordered by date descending.
    """
    # 1. Verify video ownership
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

    # 2. Fetch history
    history_stmt = (
        select(Analysis)
        .where(Analysis.video_id == video_id)
        .order_by(Analysis.created_at.desc())
    )
    history_result = await db.execute(history_stmt)
    history = history_result.scalars().all()
    return history


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_run(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches the details and execution status (e.g. pending, running, completed, failed)
    of a specific historical analysis run.
    """
    # 1. Verify analysis existence and ownership
    analysis_stmt = (
        select(Analysis)
        .join(Video)
        .join(Channel)
        .where(Analysis.id == analysis_id, Channel.creator_id == current_user.id)
    )
    analysis_result = await db.execute(analysis_stmt)
    analysis = analysis_result.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "The requested analysis run does not exist or you do not have permission to view it."
            }
        )

    return analysis


@router.get("/latest/{video_id}", response_model=AnalysisResponse)
async def get_latest_analysis(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the latest completed (or running/pending if no completed exists)
    analysis run for a video owned by the authenticated creator.
    """
    # 1. Verify video existence and ownership
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

    # 2. Get latest completed analysis run
    stmt = (
        select(Analysis)
        .where(Analysis.video_id == video_id, Analysis.status == "completed")
        .order_by(Analysis.created_at.desc())
    )
    result = await db.execute(stmt)
    analysis = result.scalars().first()

    # 3. Fallback to latest running/pending run if no completed run exists
    if not analysis:
        fallback_stmt = (
            select(Analysis)
            .where(Analysis.video_id == video_id)
            .order_by(Analysis.created_at.desc())
        )
        fallback_result = await db.execute(fallback_stmt)
        analysis = fallback_result.scalars().first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "No analysis run has been triggered for this video yet."
            }
        )

    return analysis


@router.get("/{analysis_id}/clusters", response_model=list[TopicClusterResponse])
async def get_analysis_clusters(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the topic clusters associated with a specific analysis run.
    """
    # 1. Verify analysis run exists and user owns the video
    analysis_stmt = (
        select(Analysis)
        .join(Video)
        .join(Channel)
        .where(Analysis.id == analysis_id, Channel.creator_id == current_user.id)
    )
    analysis_result = await db.execute(analysis_stmt)
    analysis = analysis_result.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "The requested analysis run does not exist or you do not have permission to view it."
            }
        )

    # 2. Fetch clusters
    clusters_stmt = (
        select(TopicCluster)
        .where(TopicCluster.analysis_id == analysis_id)
        .order_by(TopicCluster.size.desc())
    )
    clusters_result = await db.execute(clusters_stmt)
    clusters = clusters_result.scalars().all()
    return clusters



