import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, func, select

from app.modules.analysis.models import (
    Analysis,
    CommentClusterMembership,
    Insight,
    TopicCluster,
)
from app.modules.analysis.services import (
    cluster_comments_for_analysis,
    generate_insights_for_analysis,
)
from app.modules.comments.models import Comment
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video


async def _seed_video_with_comments(db) -> tuple[Video, list[Comment]]:
    user = User(email=f"membership-{uuid.uuid4()}@example.com", full_name="Test Creator")
    db.add(user)
    await db.flush()

    channel = Channel(
        creator_id=user.id,
        platform="youtube",
        external_id=f"channel-{uuid.uuid4()}",
        title="Test Channel",
    )
    db.add(channel)
    await db.flush()

    video = Video(
        channel_id=channel.id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Test Video",
        published_at=datetime.now(timezone.utc),
    )
    db.add(video)
    await db.flush()

    comments = []
    for i in range(4):
        embeddings = [1.0, 0.0] * 8 if i < 2 else [-1.0, 0.0] * 8
        comment = Comment(
            video_id=video.id,
            external_id=f"comment-{uuid.uuid4()}",
            author_name=f"Viewer {i}",
            text=f"Comment {i} asks about pricing and tutorials",
            like_count=i,
            published_at=datetime.now(timezone.utc),
            embedding=embeddings,
            sentiment_score=0.0,
        )
        db.add(comment)
        comments.append(comment)

    await db.commit()
    return video, comments


async def _membership_count(db, analysis_id) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(CommentClusterMembership)
        .where(CommentClusterMembership.analysis_id == analysis_id)
    )
    return int(result.scalar() or 0)


@pytest.mark.asyncio
async def test_reanalysis_keeps_previous_memberships(db):
    """Clustering a new analysis must not alter an earlier analysis's membership."""
    video, comments = await _seed_video_with_comments(db)

    first = Analysis(video_id=video.id, status="pending", comments_analyzed=0)
    second = Analysis(video_id=video.id, status="pending", comments_analyzed=0)
    db.add_all([first, second])
    await db.commit()

    await cluster_comments_for_analysis(db, first.id, video.id, num_clusters=2)
    await cluster_comments_for_analysis(db, second.id, video.id, num_clusters=2)

    assert await _membership_count(db, first.id) == len(comments)
    assert await _membership_count(db, second.id) == len(comments)

    # Deleting the first run's clusters must not touch the second run.
    await db.execute(delete(TopicCluster).where(TopicCluster.analysis_id == first.id))
    await db.commit()

    assert await _membership_count(db, first.id) == 0
    assert await _membership_count(db, second.id) == len(comments)


@pytest.mark.asyncio
async def test_insights_use_membership_and_echoed_cluster_id(db):
    """Insight generation reads the run's memberships and relabels by cluster_id."""
    video, comments = await _seed_video_with_comments(db)

    analysis = Analysis(video_id=video.id, status="pending", comments_analyzed=0)
    db.add(analysis)
    await db.commit()

    await cluster_comments_for_analysis(db, analysis.id, video.id, num_clusters=2)

    clusters = (
        await db.execute(
            select(TopicCluster)
            .where(TopicCluster.analysis_id == analysis.id)
            .order_by(TopicCluster.size.desc())
        )
    ).scalars().all()
    assert clusters

    response = {
        "topic_clusters": [
            {
                "cluster_id": str(cluster.id),
                "name": f"Renamed {idx}",
                "description": "A clearer group description.",
            }
            for idx, cluster in enumerate(clusters)
        ],
        "top_questions": [{"title": "Pricing?", "content": "Viewers ask about pricing."}],
        "pain_points": [],
        "positive_themes": [],
        "content_recommendations": [],
    }

    with patch(
        "app.modules.analysis.services.generate_chat_completion",
        new_callable=AsyncMock,
        return_value=json.dumps(response),
    ) as mock_llm:
        await generate_insights_for_analysis(db, analysis.id, video.id)

    prompt = mock_llm.call_args.kwargs["prompt"]
    assert all(str(cluster.id) in prompt for cluster in clusters)
    assert comments[0].text in prompt

    refreshed = (
        await db.execute(
            select(TopicCluster)
            .where(TopicCluster.analysis_id == analysis.id)
            .order_by(TopicCluster.size.desc())
        )
    ).scalars().all()
    assert all(cluster.title.startswith("Renamed ") for cluster in refreshed)

    insight_count = (
        await db.execute(
            select(func.count())
            .select_from(Insight)
            .where(Insight.analysis_id == analysis.id)
        )
    ).scalar_one()
    assert insight_count == 1
