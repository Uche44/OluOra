import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock, MagicMock

from app.modules.users.models import User, ApiQuotaUsage
from app.modules.youtube.models import Channel, Video
from app.modules.analysis.models import Analysis, AnalysisJob
from app.core.security import create_access_token
from app.modules.users.quota import (
    get_daily_quota_used,
    verify_quota_limit,
    log_youtube_quota
)
from app.modules.analysis.services import run_queued_analysis_job

pytestmark = pytest.mark.asyncio


# ... test cases ... (test_quota_tracking_and_verification & test_analyze_endpoint_quota_exceeded untouched)


async def test_quota_tracking_and_verification(db: AsyncSession):
    # 1. Create a user
    user = User(email="quota_test@gmail.com", full_name="Quota User", plan="free", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 2. Check initial quota usage
    used = await get_daily_quota_used(db, user.id)
    assert used == 0

    # 3. Verify quota passes initial ceiling
    await verify_quota_limit(db, user.id, planned_cost=10)

    # 4. Log quota consumption
    await log_youtube_quota(db, user.id, "commentThreads.list", 100)
    used = await get_daily_quota_used(db, user.id)
    assert used == 100

    # 5. Log up to the 500 limit
    await log_youtube_quota(db, user.id, "commentThreads.list", 400)
    
    # 6. Verify quota limit raises error now that ceiling is hit
    with pytest.raises(ValueError) as exc:
        await verify_quota_limit(db, user.id, planned_cost=1)
    assert str(exc.value) == "QUOTA_EXCEEDED"


async def test_analyze_endpoint_quota_exceeded(client: AsyncClient, db: AsyncSession):
    # Setup user
    user = User(email="quota_exceeded@gmail.com", full_name="Exceeded User", plan="free", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_quota_chan",
        title="Quota Channel",
        subscriber_count=10,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-quota-fail",
        title="Quota Video Fail",
        published_at=datetime.now(timezone.utc),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Force daily quota to be fully consumed (500 units)
    await log_youtube_quota(db, user.id, "commentThreads.list", 500)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Execute analyze trigger — should return 400 Bad Request
    response = await client.post(f"/api/v1/analysis/run/{video.id}", headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "QUOTA_EXCEEDED"


async def test_job_queue_creation_and_execution_success(client: AsyncClient, db: AsyncSession):
    # Setup user
    user = User(email="job_test@gmail.com", full_name="Job User", plan="free", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_job_chan",
        title="Job Channel",
        subscriber_count=10,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-job-ok",
        title="Job Video Ok",
        published_at=datetime.now(timezone.utc),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Mock the queued job processing in router to check job creation
    with patch("app.modules.analysis.router.run_queued_analysis_job") as mock_worker:
        response = await client.post(f"/api/v1/analysis/run/{video.id}", headers=headers)
        assert response.status_code == 201
        
        # Verify job row was inserted
        job_stmt = select(AnalysisJob).where(AnalysisJob.user_id == user.id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalars().first()
        assert job is not None
        assert job.status == "queued"
        assert job.attempts == 0
        assert job.video_id == video.id

        mock_worker.assert_called_once_with(job_id=job.id, google_token=None)

    # Now execute the background worker pipeline with mocked subprocesses
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("app.modules.comments.services.sync_comments_for_video", new_callable=AsyncMock) as mock_sync, \
         patch("app.modules.analysis.services.generate_embeddings_for_comments", new_callable=AsyncMock) as mock_embed, \
         patch("app.modules.analysis.services.cluster_comments_for_analysis", new_callable=AsyncMock) as mock_cluster, \
         patch("app.modules.analysis.services.generate_insights_for_analysis", new_callable=AsyncMock) as mock_insights, \
         patch("app.core.db.SessionLocal", mock_session_local):
        
        await run_queued_analysis_job(job.id, google_token="mock-token")

        # Refreshed state assertions
        db.expunge_all()
        job_stmt = select(AnalysisJob).where(AnalysisJob.id == job.id)
        job = (await db.execute(job_stmt)).scalar_one()
        assert job.status == "completed"
        assert job.attempts == 1
        assert job.completed_at is not None

        analysis_stmt = select(Analysis).where(Analysis.id == job.analysis_id)
        analysis = (await db.execute(analysis_stmt)).scalar_one()
        assert analysis.status == "completed"

        mock_sync.assert_called_once()
        mock_embed.assert_called_once()
        mock_cluster.assert_called_once()
        mock_insights.assert_called_once()
