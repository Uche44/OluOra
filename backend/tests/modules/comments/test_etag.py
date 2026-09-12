import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import Response

from app.integrations.youtube import fetch_comment_threads
from app.modules.youtube.models import Video, Channel
from app.modules.users.models import User
from app.modules.comments.services import sync_comments_for_video
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_fetch_comment_threads_etag_handling():
    # 1. Test HTTP 304 Not Modified
    mock_response_304 = MagicMock(spec=Response)
    mock_response_304.status_code = 304

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response_304
        res = await fetch_comment_threads(
            access_token="test-token",
            video_id="vid-1",
            etag="etag-abc"
        )
        assert res == {"etag_matched": True}
        # Check header was passed correctly
        headers_called = mock_get.call_args[1]["headers"]
        assert headers_called["If-None-Match"] == "etag-abc"

    # 2. Test HTTP 200 OK with ETag header
    mock_response_200 = MagicMock(spec=Response)
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"items": []}
    mock_response_200.headers = {"etag": "etag-new-123"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response_200
        res = await fetch_comment_threads(
            access_token="test-token",
            video_id="vid-1"
        )
        assert res["items"] == []
        assert res["_etag"] == "etag-new-123"


async def test_sync_comments_etag_match_returns_zero(db: AsyncSession):
    # Setup test models
    user = User(email="etag_sync@gmail.com", plan="free")
    db.add(user)
    await db.commit()

    channel = Channel(creator_id=user.id, external_id="UC_etag", title="Chan")
    db.add(channel)
    await db.commit()

    video = Video(
        channel_id=channel.id,
        external_id="video-etag-304",
        title="ETag Video",
        published_at=datetime.now(timezone.utc),
        etag="cached-etag-456"
    )
    db.add(video)
    await db.commit()

    # Mock fetch_comment_threads to return etag_matched=True
    with patch("app.integrations.youtube.fetch_comment_threads", new_callable=AsyncMock) as mock_fetch, \
         patch("app.modules.comments.services.log_api_quota", new_callable=AsyncMock) as mock_log_quota:
        
        mock_fetch.return_value = {"etag_matched": True}

        # Run comments sync
        count = await sync_comments_for_video(db, video, "token")
        assert count == 0

        # Assert no quota logged since it was 304 Not Modified
        mock_log_quota.assert_not_called()
        
        # Verify etag parameter was forwarded
        mock_fetch.assert_called_once_with(
            access_token="token",
            video_id="video-etag-304",
            max_results=100,
            page_token=None,
            etag="cached-etag-456"
        )


async def test_sync_comments_new_etag_updates_video(db: AsyncSession):
    # Setup models
    user = User(email="etag_new@gmail.com", plan="free")
    db.add(user)
    await db.commit()

    channel = Channel(creator_id=user.id, external_id="UC_etag_new", title="Chan")
    db.add(channel)
    await db.commit()

    video = Video(
        channel_id=channel.id,
        external_id="video-etag-new",
        title="ETag Video New",
        published_at=datetime.now(timezone.utc),
        etag="old-etag"
    )
    db.add(video)
    await db.commit()

    # Mock fetch_comment_threads to return a successful page list with a new ETag
    with patch("app.integrations.youtube.fetch_comment_threads", new_callable=AsyncMock) as mock_fetch, \
         patch("app.modules.comments.services.log_api_quota", new_callable=AsyncMock):
        
        mock_fetch.return_value = {
            "items": [],
            "_etag": "newly-obtained-etag"
        }

        # Run comments sync
        count = await sync_comments_for_video(db, video, "token")
        assert count == 0

        # Verify ETag column has been updated in the DB
        await db.refresh(video)
        assert video.etag == "newly-obtained-etag"
