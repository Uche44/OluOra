import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.core.security import create_access_token
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio


async def _make_user_with_tiktok(db: AsyncSession, email: str, expires_in_minutes: int = 60):
    user = User(email=email, full_name="TikTok Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    social = SocialAccount(
        user_id=user.id,
        provider=providers.TIKTOK,
        provider_user_id="open-id-sync",
        access_token="act.valid",
        refresh_token="rft.valid",
        token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db.add(social)
    await db.commit()
    return user, social


async def test_tiktok_sync_success(client: AsyncClient, db: AsyncSession):
    user, _ = await _make_user_with_tiktok(db, "tiktok_sync@example.com")
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.integrations.tiktok.fetch_user_info", new_callable=AsyncMock) as mock_user_info, \
         patch("app.integrations.tiktok.fetch_user_videos", new_callable=AsyncMock) as mock_videos:
        mock_user_info.return_value = {
            "open_id": "open-id-sync",
            "display_name": "Sync Creator",
            "bio_description": "Clips",
            "avatar_url": "https://example.com/a.jpg",
            "follower_count": 900,
            "video_count": 2,
        }
        mock_videos.return_value = {
            "videos": [
                {"id": "v1", "title": "One", "create_time": 1750000000, "view_count": 10,
                 "like_count": 1, "comment_count": 0, "cover_image_url": "https://example.com/1.jpg"},
                {"id": "v2", "title": "Two", "create_time": 1749990000, "view_count": 20,
                 "like_count": 2, "comment_count": 3, "cover_image_url": "https://example.com/2.jpg"},
            ],
            "has_more": False,
        }

        response = await client.post("/api/v1/tiktok/sync?limit=50", headers=headers)

    assert response.status_code == 200
    assert response.json()["videos_imported"] == 2

    channel = (await db.execute(
        select(Channel).where(Channel.creator_id == user.id, Channel.platform == providers.TIKTOK)
    )).scalar_one()
    assert channel.external_id == "open-id-sync"
    assert channel.subscriber_count == 900

    videos = (await db.execute(
        select(Video).where(Video.channel_id == channel.id).order_by(Video.external_id)
    )).scalars().all()
    assert [v.external_id for v in videos] == ["v1", "v2"]
    assert all(v.platform == providers.TIKTOK for v in videos)
    assert videos[1].comment_count == 3


async def test_tiktok_sync_paginates(client: AsyncClient, db: AsyncSession):
    user, _ = await _make_user_with_tiktok(db, "tiktok_pages@example.com")
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.integrations.tiktok.fetch_user_info", new_callable=AsyncMock) as mock_user_info, \
         patch("app.integrations.tiktok.fetch_user_videos", new_callable=AsyncMock) as mock_videos:
        mock_user_info.return_value = {"open_id": "open-id-sync", "display_name": "Paged"}
        mock_videos.side_effect = [
            {"videos": [{"id": "p1", "title": "P1", "create_time": 1750000000}], "cursor": 111, "has_more": True},
            {"videos": [{"id": "p2", "title": "P2", "create_time": 1749990000}], "cursor": 222, "has_more": False},
        ]

        response = await client.post("/api/v1/tiktok/sync?limit=50", headers=headers)

    assert response.status_code == 200
    assert response.json()["videos_imported"] == 2
    assert mock_videos.call_count == 2


async def test_tiktok_sync_persists_rotated_refresh_token(client: AsyncClient, db: AsyncSession):
    # Expired access token forces a refresh; TikTok may return a NEW refresh token.
    user, social = await _make_user_with_tiktok(db, "tiktok_refresh@example.com", expires_in_minutes=-10)
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.integrations.tiktok.refresh_access_token", new_callable=AsyncMock) as mock_refresh, \
         patch("app.integrations.tiktok.fetch_user_info", new_callable=AsyncMock) as mock_user_info, \
         patch("app.integrations.tiktok.fetch_user_videos", new_callable=AsyncMock) as mock_videos:
        mock_refresh.return_value = {
            "access_token": "act.refreshed",
            "refresh_token": "rft.rotated",
            "expires_in": 86400,
            "refresh_expires_in": 31536000,
        }
        mock_user_info.return_value = {"open_id": "open-id-sync", "display_name": "Refreshed"}
        mock_videos.return_value = {"videos": [], "has_more": False}

        response = await client.post("/api/v1/tiktok/sync", headers=headers)

    assert response.status_code == 200
    mock_refresh.assert_called_once_with("rft.valid")

    await db.refresh(social)
    assert social.access_token == "act.refreshed"
    assert social.refresh_token == "rft.rotated"


async def test_tiktok_sync_without_connection(client: AsyncClient, db: AsyncSession):
    user = User(email="tiktok_unconnected@example.com", full_name="No TikTok", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/tiktok/sync", headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ACCOUNT_NOT_CONNECTED"


async def test_tiktok_comments_are_not_supported(client: AsyncClient, db: AsyncSession):
    user, _ = await _make_user_with_tiktok(db, "tiktok_comments@example.com")
    channel = Channel(
        creator_id=user.id,
        platform=providers.TIKTOK,
        external_id="open-id-sync",
        title="TikTok Channel",
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        platform=providers.TIKTOK,
        external_id="tt-video-1",
        title="TikTok video",
        published_at=datetime.now(timezone.utc),
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    comments_res = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)
    assert comments_res.status_code == 400
    assert comments_res.json()["detail"]["code"] == "COMMENTS_NOT_SUPPORTED"

    analysis_res = await client.post(f"/api/v1/analysis/run/{video.id}", headers=headers)
    assert analysis_res.status_code == 400
    assert analysis_res.json()["detail"]["code"] == "COMMENTS_NOT_SUPPORTED"
