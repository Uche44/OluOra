import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.analysis.models import Analysis, TopicCluster, Insight

pytestmark = pytest.mark.asyncio

async def test_full_database_relationships_and_cascades(db: AsyncSession):
    # 1. Create User
    user = User(
        email="creator@oluora.com",
        full_name="Olu Creator",
        profile_picture="https://example.com/pic.jpg",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.id is not None
    assert user.email == "creator@oluora.com"

    # 2. Create SocialAccount linked to User
    social = SocialAccount(
        user_id=user.id,
        provider="youtube",
        provider_user_id="google-12345",
        access_token="access-token-xyz",
        refresh_token="refresh-token-xyz",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(social)
    await db.commit()
    await db.refresh(social)

    assert social.id is not None
    assert social.user_id == user.id

    # 3. Create Channel managed by user
    channel = Channel(
        creator_id=user.id,
        external_id="UC1234567890",
        title="Olu Tech Reviews",
        description="YouTube Channel for tech reviews",
        subscriber_count=10000,
        video_count=50
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    assert channel.id is not None
    assert channel.creator_id == user.id

    # 4. Create Video belonging to Channel
    video = Video(
        channel_id=channel.id,
        external_id="video-xyz123",
        title="My First Video Review",
        description="Reviewing new tech devices",
        published_at=datetime.now(timezone.utc),
        view_count=500,
        like_count=45,
        comment_count=2,
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    assert video.id is not None
    assert video.channel_id == channel.id

    # 5. Create Parent Comment and a Child Reply (self-referencing threads)
    parent_comment = Comment(
        video_id=video.id,
        external_id="comment-1",
        author_name="Viewer A",
        text="This video is awesome!",
        like_count=5,
        published_at=datetime.now(timezone.utc)
    )
    db.add(parent_comment)
    await db.commit()
    await db.refresh(parent_comment)

    child_reply = Comment(
        video_id=video.id,
        external_id="reply-1",
        author_name="Olu Creator",
        text="Thank you for watching!",
        like_count=2,
        published_at=datetime.now(timezone.utc),
        parent_id=parent_comment.id
    )
    db.add(child_reply)
    await db.commit()
    await db.refresh(child_reply)

    # Verify hierarchical relationships
    from sqlalchemy.orm import selectinload
    query = select(Comment).where(Comment.id == parent_comment.id).options(selectinload(Comment.replies))
    result = await db.execute(query)
    parent = result.scalar_one()
    
    assert len(parent.replies) == 1
    assert parent.replies[0].text == "Thank you for watching!"
    assert parent.replies[0].parent_id == parent.id

    # 6. Create Analysis, TopicCluster, and Insight
    analysis = Analysis(
        video_id=video.id,
        status="completed",
        comments_analyzed=2
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    cluster = TopicCluster(
        analysis_id=analysis.id,
        title="Video Feedback",
        summary="Positive feedback from the audience",
        size=1,
        sentiment_score=0.9
    )
    db.add(cluster)

    insight = Insight(
        analysis_id=analysis.id,
        type="content_idea",
        title="Tech Specs Insight",
        content="Viewers want more technical details in future reviews"
    )
    db.add(insight)
    await db.commit()

    # Verify relationships
    query = select(Analysis).where(Analysis.id == analysis.id).options(
        selectinload(Analysis.topic_clusters),
        selectinload(Analysis.insights)
    )
    result = await db.execute(query)
    analysis = result.scalar_one()
    
    assert len(analysis.topic_clusters) == 1
    assert len(analysis.insights) == 1
    assert analysis.topic_clusters[0].title == "Video Feedback"
    assert analysis.insights[0].type == "content_idea"

    # 7. Test Cascade Delete
    # Deleting the video should cascade delete comments and analyses
    await db.delete(video)
    await db.commit()

    # Verify comments and analysis are gone
    comments_result = await db.execute(select(Comment).where(Comment.video_id == video.id))
    assert len(comments_result.scalars().all()) == 0

    analysis_result = await db.execute(select(Analysis).where(Analysis.video_id == video.id))
    assert len(analysis_result.scalars().all()) == 0

    # Verify clusters and insights are cascade deleted too (via analysis cascade delete)
    clusters_result = await db.execute(select(TopicCluster).where(TopicCluster.analysis_id == analysis.id))
    assert len(clusters_result.scalars().all()) == 0
