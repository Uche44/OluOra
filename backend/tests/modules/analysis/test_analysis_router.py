import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from unittest.mock import patch

from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video
from app.modules.analysis.models import Analysis, Insight
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_get_analysis_insights_success(client: AsyncClient, db: AsyncSession):
    # 1. Setup user, channel, video, analysis, and insights
    user = User(email="insights_creator@gmail.com", full_name="Insights Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_insights_router",
        title="Insights Channel",
        subscriber_count=5000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-insights-router",
        title="Testing Router Insights",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    analysis = Analysis(
        video_id=video.id,
        status="completed",
        comments_analyzed=100
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Add mock insights of different types
    insights_to_add = [
        Insight(analysis_id=analysis.id, type="question", title="Pricing", content="Is this free?"),
        Insight(analysis_id=analysis.id, type="pain_point", title="Slow load", content="Takes 10s to load."),
        Insight(analysis_id=analysis.id, type="positive_theme", title="UX", content="Love the theme."),
        # Add recommendation (which should not be returned by the insights endpoint)
        Insight(analysis_id=analysis.id, type="recommendation", title="Pricing video", content="Make video about pricing.")
    ]
    for insight in insights_to_add:
        db.add(insight)
    await db.commit()

    # 2. Call the GET insights endpoint
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/analysis/{analysis.id}/insights", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "questions" in data
    assert "pain_points" in data
    assert "positive_themes" in data

    # Verify filtering and mappings
    assert len(data["questions"]) == 1
    assert data["questions"][0]["title"] == "Pricing"
    assert data["questions"][0]["content"] == "Is this free?"

    assert len(data["pain_points"]) == 1
    assert data["pain_points"][0]["title"] == "Slow load"

    assert len(data["positive_themes"]) == 1
    assert data["positive_themes"][0]["title"] == "UX"


async def test_get_analysis_insights_unauthorized(client: AsyncClient, db: AsyncSession):
    # Try calling without auth headers
    response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/insights")
    assert response.status_code == 401


async def test_get_analysis_insights_not_found(client: AsyncClient, db: AsyncSession):
    # Setup user
    user = User(email="insights_other@gmail.com", full_name="Other Insights User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Request comments for a random UUID analysis which does not exist
    response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/insights", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "ANALYSIS_NOT_FOUND"


async def test_get_analysis_recommendations_success(client: AsyncClient, db: AsyncSession):
    # Setup user, channel, video, analysis, and insights
    user = User(email="rec_creator@gmail.com", full_name="Rec Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_recs_router",
        title="Recs Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-recs-router",
        title="Testing Router Recommendations",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    analysis = Analysis(
        video_id=video.id,
        status="completed",
        comments_analyzed=100
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Add mock insights of different types
    insights_to_add = [
        Insight(analysis_id=analysis.id, type="question", title="Pricing", content="Is this free?"),
        Insight(analysis_id=analysis.id, type="recommendation", title="Pricing video", content="Make video about pricing.")
    ]
    for insight in insights_to_add:
        db.add(insight)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/analysis/{analysis.id}/recommendations", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["type"] == "recommendation"
    assert data[0]["title"] == "Pricing video"
    assert data[0]["content"] == "Make video about pricing."


async def test_get_analysis_recommendations_unauthorized(client: AsyncClient, db: AsyncSession):
    # Try calling without auth headers
    response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/recommendations")
    assert response.status_code == 401


async def test_get_analysis_recommendations_not_found(client: AsyncClient, db: AsyncSession):
    user = User(email="rec_other@gmail.com", full_name="Other Recs User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Request recommendations for a random UUID analysis which does not exist
    response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/recommendations", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "ANALYSIS_NOT_FOUND"


async def test_run_analysis_success(client: AsyncClient, db: AsyncSession):
    # Setup user, channel, video
    user = User(email="run_creator@gmail.com", full_name="Run Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_run_router",
        title="Run Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-run-router",
        title="Testing Router Run",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Mock the background task execution
    with patch("app.modules.analysis.router.run_queued_analysis_job") as mock_background_task:
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(f"/api/v1/analysis/run/{video.id}", headers=headers)
        assert response.status_code == 201

        data = response.json()
        assert data["video_id"] == str(video.id)
        assert data["status"] == "pending"
        assert "id" in data

        # Check background task was added
        mock_background_task.assert_called_once()


async def test_get_analysis_history_success(client: AsyncClient, db: AsyncSession):
    # Setup user, channel, video, and historical runs
    user = User(email="hist_creator@gmail.com", full_name="Hist Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_hist_router",
        title="Hist Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-hist-router",
        title="Testing Router History",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Add 2 historical runs with distinct created_at times to avoid sorting ambiguity
    analysis1 = Analysis(video_id=video.id, status="completed", comments_analyzed=50)
    analysis2 = Analysis(video_id=video.id, status="failed", comments_analyzed=0, error_message="API Limit")
    db.add(analysis1)
    db.add(analysis2)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/analysis/history/{video.id}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Should be sorted by created_at descending (latest first)
    assert data[0]["status"] == "failed"
    assert data[1]["status"] == "completed"


async def test_get_analysis_run_details(client: AsyncClient, db: AsyncSession):
    # Setup user, channel, video, and analysis
    user = User(email="run_det_creator@gmail.com", full_name="Run Det Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_run_det_router",
        title="Run Det Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-run-det-router",
        title="Testing Router Run Det",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    analysis = Analysis(video_id=video.id, status="running", comments_analyzed=10)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/analysis/{analysis.id}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(analysis.id)
    assert data["status"] == "running"
    assert data["comments_analyzed"] == 10


async def test_get_latest_analysis_success(client: AsyncClient, db: AsyncSession):
    # Setup user, channel, video
    user = User(email="latest_creator@gmail.com", full_name="Latest Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_latest_router",
        title="Latest Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-latest-router",
        title="Testing Router Latest",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Create one pending analysis and one completed analysis
    analysis_pending = Analysis(video_id=video.id, status="pending", comments_analyzed=0)
    db.add(analysis_pending)
    await db.commit()

    analysis_completed = Analysis(video_id=video.id, status="completed", comments_analyzed=20)
    db.add(analysis_completed)
    await db.commit()
    await db.refresh(analysis_completed)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Should fetch the completed one because it takes priority
    response = await client.get(f"/api/v1/analysis/latest/{video.id}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(analysis_completed.id)
    assert data["status"] == "completed"


async def test_get_analysis_clusters_success(client: AsyncClient, db: AsyncSession):
    from app.modules.analysis.models import TopicCluster
    
    # Setup user, channel, video, analysis
    user = User(email="clusters_creator@gmail.com", full_name="Clusters Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_clusters_router",
        title="Clusters Channel",
        subscriber_count=1000,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-clusters-router",
        title="Testing Router Clusters",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    analysis = Analysis(video_id=video.id, status="completed", comments_analyzed=100)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Add clusters
    cluster1 = TopicCluster(analysis_id=analysis.id, title="Pricing", summary="Pricing setup", size=60, sentiment_score=0.8)
    cluster2 = TopicCluster(analysis_id=analysis.id, title="UX", summary="UX theme", size=40, sentiment_score=0.9)
    db.add(cluster1)
    db.add(cluster2)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/analysis/{analysis.id}/clusters", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Should be sorted by size desc
    assert data[0]["title"] == "Pricing"
    assert data[0]["size"] == 60
    assert data[1]["title"] == "UX"
    assert data[1]["size"] == 40

