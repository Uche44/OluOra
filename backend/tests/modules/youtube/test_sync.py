import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio

@patch("app.integrations.youtube.fetch_channel_details", new_callable=AsyncMock)
@patch("app.integrations.youtube.fetch_latest_videos", new_callable=AsyncMock)
@patch("app.integrations.youtube.fetch_videos_metadata", new_callable=AsyncMock)
async def test_youtube_sync_success(
    mock_fetch_meta,
    mock_fetch_latest,
    mock_fetch_channel,
    client: AsyncClient,
    db: AsyncSession
):
    # 1. Create creator user and Google social connection
    user = User(
        email="sync_creator@gmail.com",
        full_name="Sync Creator",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    social = SocialAccount(
        user_id=user.id,
        provider="youtube",
        provider_user_id="google-id-creator-111",
        access_token="google-valid-access-token",
        refresh_token="google-valid-refresh-token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(social)
    await db.commit()

    # 2. Setup YouTube API mocks
    mock_fetch_channel.return_value = {
        "id": "UC_channel_123",
        "snippet": {
            "title": "Olu Tech Reviews",
            "description": "Premium tech review uploads",
            "thumbnails": {"high": {"url": "https://example.com/channel.jpg"}}
        },
        "statistics": {
            "subscriberCount": "15000",
            "videoCount": "4"
        },
        "contentDetails": {
            "relatedPlaylists": {
                "uploads": "UU_channel_123"
            }
        }
    }

    mock_fetch_latest.return_value = ["video-id-001", "video-id-002"]

    mock_fetch_meta.return_value = [
        {
            "id": "video-id-001",
            "snippet": {
                "title": "Unboxing Phone 16",
                "description": "Hands on with the new phone",
                "publishedAt": "2026-07-06T12:00:00Z",
                "thumbnails": {"high": {"url": "https://example.com/phone.jpg"}}
            },
            "statistics": {
                "viewCount": "1200",
                "likeCount": "95",
                "commentCount": "22"
            }
        },
        {
            "id": "video-id-002",
            "snippet": {
                "title": "Smart Watch Review",
                "description": "Analyzing smart watch features",
                "publishedAt": "2026-07-05T15:00:00Z",
                "thumbnails": {"high": {"url": "https://example.com/watch.jpg"}}
            },
            "statistics": {
                "viewCount": "900",
                "likeCount": "70",
                "commentCount": "14"
            }
        }
    ]

    # 3. Call sync endpoint with bearer JWT auth
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post("/api/v1/youtube/sync?limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["videos_imported"] == 2

    # 4. Verify DB items
    channel_query = select(Channel).where(Channel.creator_id == user.id)
    channel_res = await db.execute(channel_query)
    channel = channel_res.scalar_one_or_none()
    assert channel is not None
    assert channel.external_id == "UC_channel_123"
    assert channel.title == "Olu Tech Reviews"
    assert channel.subscriber_count == 15000

    videos_query = select(Video).where(Video.channel_id == channel.id).order_by(Video.published_at.desc())
    videos_res = await db.execute(videos_query)
    videos = videos_res.scalars().all()
    assert len(videos) == 2
    assert videos[0].external_id == "video-id-001"
    assert videos[0].title == "Unboxing Phone 16"
    assert videos[0].comment_count == 22
    assert videos[1].external_id == "video-id-002"

@patch("app.integrations.google.refresh_google_access_token", new_callable=AsyncMock)
@patch("app.integrations.youtube.fetch_channel_details", new_callable=AsyncMock)
@patch("app.integrations.youtube.fetch_latest_videos", new_callable=AsyncMock)
@patch("app.integrations.youtube.fetch_videos_metadata", new_callable=AsyncMock)
async def test_youtube_sync_token_expired_refresh(
    mock_fetch_meta,
    mock_fetch_latest,
    mock_fetch_channel,
    mock_refresh_token,
    client: AsyncClient,
    db: AsyncSession
):
    # 1. Create user and EXPIRED Google social account (token_expires_at in past)
    user = User(
        email="expired_token@gmail.com",
        full_name="Expired Token Tester",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    social = SocialAccount(
        user_id=user.id,
        provider="youtube",
        provider_user_id="google-id-expired-333",
        access_token="expired-access-token",
        refresh_token="valid-refresh-token",
        token_expires_at=expired_time
    )
    db.add(social)
    await db.commit()

    # 2. Setup mocks
    mock_refresh_token.return_value = {
        "access_token": "newly-refreshed-google-access-token",
        "expires_in": 3600
    }
    
    mock_fetch_channel.return_value = {
        "id": "UC_channel_refresh",
        "snippet": {"title": "Refreshed Channel"},
        "statistics": {"subscriberCount": "100", "videoCount": "0"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UU_channel_refresh"}}
    }
    mock_fetch_latest.return_value = []
    
    # 3. Trigger sync call
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post("/api/v1/youtube/sync", headers=headers)
    assert response.status_code == 200
    
    # Verify mock refresh was executed
    mock_refresh_token.assert_called_once_with("valid-refresh-token")
    
    # Verify DB social account tokens updated
    await db.refresh(social)
    assert social.access_token == "newly-refreshed-google-access-token"
    assert social.token_expires_at > datetime.now(timezone.utc)

async def test_youtube_sync_no_connected_account(client: AsyncClient, db: AsyncSession):
    # Create user with NO connected social account
    user = User(
        email="unconnected_creator@gmail.com",
        full_name="Unconnected Creator",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post("/api/v1/youtube/sync", headers=headers)
    assert response.status_code == 400
    
    data = response.json()
    assert data["detail"]["code"] == "ACCOUNT_NOT_CONNECTED"
    assert "no connected youtube account" in data["detail"]["message"].lower()
