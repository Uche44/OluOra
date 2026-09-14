import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.integrations import tiktok
from app.modules.users.models import User, SocialAccount
from app.modules.users.schemas import (
    UserUpdate, 
    UserProfileResponse, 
    ConnectedAccountSchema, 
    ConnectedChannelSchema,
    DashboardStatsResponse,
    DashboardMetricSchema,
    DashboardActionSchema
)
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.analysis.models import Analysis, Insight, TopicCluster

router = APIRouter(prefix="/users", tags=["Users"])


async def _load_profile_parts(db: AsyncSession, user_id):
    """Load a user's connected data accounts and channels."""
    social_result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == user_id)
    )
    socials = social_result.scalars().all()

    channel_result = await db.execute(
        select(Channel).where(Channel.creator_id == user_id)
    )
    channels = channel_result.scalars().all()
    return socials, channels


def _serialize_profile(user: User, socials, channels) -> UserProfileResponse:
    connections = [
        ConnectedAccountSchema(
            provider=s.provider,
            provider_user_id=s.provider_user_id,
            token_expires_at=s.token_expires_at
        ) for s in socials
    ]

    channels_data = [
        ConnectedChannelSchema(
            id=c.id,
            platform=c.platform,
            external_id=c.external_id,
            title=c.title,
            description=c.description,
            thumbnail_url=c.thumbnail_url,
            subscriber_count=c.subscriber_count,
            video_count=c.video_count
        ) for c in channels
    ]

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        profile_picture=user.profile_picture,
        is_active=user.is_active,
        auth_provider=user.auth_provider,
        created_at=user.created_at,
        connections=connections,
        channels=channels_data
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current user details, connected data accounts, and connected channels."""
    socials, channels = await _load_profile_parts(db, current_user.id)
    return _serialize_profile(current_user, socials, channels)


@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates user's profile details."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.profile_picture is not None:
        current_user.profile_picture = payload.profile_picture
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    socials, channels = await _load_profile_parts(db, current_user.id)
    return _serialize_profile(current_user, socials, channels)


@router.post("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnects a data provider, removing only that platform's channels and credentials."""
    # Find social account
    social_query = select(SocialAccount).where(
        SocialAccount.user_id == current_user.id,
        SocialAccount.provider == provider
    )
    social_result = await db.execute(social_query)
    social = social_result.scalar_one_or_none()

    if not social:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONNECTION_NOT_FOUND",
                "message": f"No connected connection found for provider '{provider}'."
            }
        )

    # Best-effort provider-side revocation before dropping local credentials.
    if provider == providers.TIKTOK:
        await tiktok.revoke_access_token(social.access_token)

    # Delete only this platform's channels (cascade-deletes their videos/comments/analyses)
    channel_query = select(Channel).where(
        Channel.creator_id == current_user.id,
        Channel.platform == provider
    )
    channel_result = await db.execute(channel_query)
    channels = channel_result.scalars().all()
    for channel in channels:
        await db.delete(channel)

    await db.delete(social)
    await db.commit()

    return {
        "status": "success",
        "message": f"Successfully disconnected provider '{provider}' and removed all associated channel analytics."
    }


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Aggregates and returns live statistics, summary cards, and recommended actions for the creator dashboard."""
    from datetime import datetime

    # 1. Videos Analyzed: count of videos where sync_status is 'completed'
    videos_query = select(func.count(Video.id)).join(Channel).where(
        Channel.creator_id == current_user.id,
        Video.sync_status == "completed"
    )
    videos_result = await db.execute(videos_query)
    videos_analyzed = videos_result.scalar_one()

    # 2. Comments Processed: count of comments in DB for user's videos
    comments_query = select(func.count(Comment.id)).join(Video).join(Channel).where(
        Channel.creator_id == current_user.id
    )
    comments_result = await db.execute(comments_query)
    comments_processed = comments_result.scalar_one()

    # 3. Questions Discovered: count of insights of type 'question'
    questions_query = select(func.count(Insight.id)).join(Analysis).join(Video).join(Channel).where(
        Channel.creator_id == current_user.id,
        Insight.type == "question"
    )
    questions_result = await db.execute(questions_query)
    questions_discovered = questions_result.scalar_one()

    # 4. Sentiment Score: average of all Comment.sentiment_score values (usually -1 to 1)
    sentiment_query = select(func.avg(Comment.sentiment_score)).join(Video).join(Channel).where(
        Channel.creator_id == current_user.id,
        Comment.sentiment_score.is_not(None)
    )
    sentiment_result = await db.execute(sentiment_query)
    avg_sentiment = sentiment_result.scalar()
    
    if avg_sentiment is not None:
        # Map from [-1.0, 1.0] -> [0, 100]
        sentiment_score = int((avg_sentiment + 1.0) * 50.0)
    else:
        # Default to a nice mock like 75 if no comments have been scored yet
        sentiment_score = 75

    # 5. Latest Analysis & Summary Details
    latest_analysis_stmt = (
        select(Analysis)
        .join(Video)
        .join(Channel)
        .where(
            Channel.creator_id == current_user.id,
            Analysis.status == "completed"
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    latest_analysis_res = await db.execute(latest_analysis_stmt)
    latest_analysis = latest_analysis_res.scalar_one_or_none()

    summary_title = "Welcome to OluOra"
    summary_content = "To get started, sync a video from your video library to generate AI summaries and discover content opportunities."
    summary_date = datetime.now().strftime("%B %d, %Y")
    summary_metrics = [
        DashboardMetricSchema(label="Analyzed", value="0 comments"),
        DashboardMetricSchema(label="Issues / Questions", value="0 found")
    ]
    recent_actions = []

    if latest_analysis:
        # Fetch the video details
        video_stmt = select(Video).where(Video.id == latest_analysis.video_id)
        video_res = await db.execute(video_stmt)
        latest_video = video_res.scalar_one_or_none()
        video_title = latest_video.title if latest_video else "Latest Upload"

        summary_title = "Today's Summary"
        summary_date = latest_analysis.created_at.strftime("%B %d, %Y")

        # Fetch top cluster details to make a smart summary statement
        clusters_stmt = select(TopicCluster).where(TopicCluster.analysis_id == latest_analysis.id).order_by(TopicCluster.size.desc())
        clusters_res = await db.execute(clusters_stmt)
        clusters = clusters_res.scalars().all()

        total_cluster_comments = sum(c.size for c in clusters)
        if clusters:
            top_cluster = clusters[0]
            pct = int((top_cluster.size / total_cluster_comments) * 100) if total_cluster_comments > 0 else 0
            summary_content = (
                f"We completed the audience analysis of your video '{video_title}'. "
                f"Viewers are highly engaged around the theme of '{top_cluster.title}' which accounts for {pct}% of comments. "
                f"Here is your compiled audience pulse."
            )
        else:
            summary_content = f"Analysis of video '{video_title}' completed with {latest_analysis.comments_analyzed} comments processed."

        # Fetch count of unresolved questions/pain points
        unresolved_stmt = select(func.count(Insight.id)).where(
            Insight.analysis_id == latest_analysis.id,
            Insight.type.in_(["question", "pain_point"])
        )
        unresolved_res = await db.execute(unresolved_stmt)
        unresolved_count = unresolved_res.scalar_one()

        summary_metrics = [
            DashboardMetricSchema(label="Analyzed", value=f"{latest_analysis.comments_analyzed} comments"),
            DashboardMetricSchema(label="Issues / Questions", value=f"{unresolved_count} found")
        ]

        # Fetch recent recommendations
        recs_stmt = select(Insight).where(
            Insight.analysis_id == latest_analysis.id,
            Insight.type == "recommendation"
        ).limit(3)
        recs_res = await db.execute(recs_stmt)
        recs = recs_res.scalars().all()

        # Types and button layouts rotation to match different design cards
        action_types = ["alert", "trend", "opt"]
        button_texts = ["Add to Script", "Research Topic", "Review Opportunity"]

        for idx, rec in enumerate(recs):
            rec_type = action_types[idx % len(action_types)]
            btn_text = button_texts[idx % len(button_texts)]
            recent_actions.append(
                DashboardActionSchema(
                    id=rec.id,
                    type=rec_type,
                    title=rec.title,
                    description=rec.content,
                    buttonText=btn_text
                )
            )

    # Let's map growth_score. If we have a video, calculate a mock score based on engagement
    growth_score = min(99, max(60, int(sentiment_score * 0.8 + 20)))

    return DashboardStatsResponse(
        videos_analyzed=videos_analyzed,
        comments_processed=comments_processed,
        questions_discovered=questions_discovered,
        sentiment_score=sentiment_score,
        growth_score=growth_score,
        summary_title=summary_title,
        summary_content=summary_content,
        summary_date=summary_date,
        summary_metrics=summary_metrics,
        recent_actions=recent_actions
    )


