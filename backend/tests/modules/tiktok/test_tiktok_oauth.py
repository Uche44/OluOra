import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.core.config import settings
from app.core.security import create_access_token
from app.integrations.oauth_state import create_oauth_state
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel

pytestmark = pytest.mark.asyncio


async def test_tiktok_url_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/tiktok/url")
    assert response.status_code in (401, 403)


async def test_tiktok_url_forbidden_when_not_allowlisted(client: AsyncClient, db: AsyncSession):
    user = User(email="tiktok_not_beta@example.com", full_name="Not Beta", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(settings, "TIKTOK_BETA_EMAILS", "someone_else@example.com"):
        response = await client.get("/api/v1/auth/tiktok/url", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "TIKTOK_NOT_AVAILABLE"


async def test_tiktok_url_returns_consent_url(client: AsyncClient, db: AsyncSession):
    user = User(email="tiktok_url@example.com", full_name="TikTok URL", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(settings, "TIKTOK_BETA_EMAILS", "tiktok_url@example.com"), \
         patch.object(settings, "TIKTOK_CLIENT_KEY", "test-client-key"), \
         patch.object(settings, "TIKTOK_REDIRECT_URI", "https://example.com/auth/tiktok/callback"):
        response = await client.get("/api/v1/auth/tiktok/url", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "tiktok.com/v2/auth/authorize" in data["url"]
    assert "video.list" in data["url"]
    assert "client_key=test-client-key" in data["url"]
    assert data["state"]


async def test_tiktok_callback_rejects_wrong_flow_state(client: AsyncClient, db: AsyncSession):
    user = User(email="tiktok_badstate@example.com", full_name="Bad State", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # A login-flow state must not be reusable to connect TikTok.
    state = create_oauth_state(providers.FLOW_LOGIN, user_id=user.id)
    with patch.object(settings, "TIKTOK_BETA_EMAILS", "tiktok_badstate@example.com"):
        response = await client.post(
            "/api/v1/auth/tiktok/callback", json={"code": "abc", "state": state}, headers=headers
        )
    assert response.status_code == 400


async def test_tiktok_callback_forbidden_when_not_allowlisted(
    client: AsyncClient, db: AsyncSession
):
    user = User(email="tiktok_cb_not_beta@example.com", full_name="Not Beta", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    state = create_oauth_state(providers.FLOW_TIKTOK_CONNECT, user_id=user.id)

    with patch.object(settings, "TIKTOK_BETA_EMAILS", "someone_else@example.com"):
        response = await client.post(
            "/api/v1/auth/tiktok/callback", json={"code": "abc", "state": state}, headers=headers
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "TIKTOK_NOT_AVAILABLE"


async def test_tiktok_callback_connects_account(client: AsyncClient, db: AsyncSession):
    user = User(email="tiktok_connect@example.com", full_name="TikTok Connect", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    state = create_oauth_state(providers.FLOW_TIKTOK_CONNECT, user_id=user.id)

    with patch.object(settings, "TIKTOK_BETA_EMAILS", "tiktok_connect@example.com"), \
         patch("app.integrations.tiktok.exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange, \
         patch("app.integrations.tiktok.fetch_user_info", new_callable=AsyncMock) as mock_user_info, \
         patch("app.integrations.tiktok.fetch_user_videos", new_callable=AsyncMock) as mock_videos:
        mock_exchange.return_value = {
            "access_token": "act.token",
            "refresh_token": "rft.token",
            "open_id": "open-id-123",
            "expires_in": 86400,
            "refresh_expires_in": 31536000,
            "scope": "user.info.basic,video.list",
        }
        mock_user_info.return_value = {
            "open_id": "open-id-123",
            "display_name": "TikTok Creator",
            "username": "tikcreator",
            "bio_description": "Daily clips",
            "avatar_url": "https://example.com/avatar.jpg",
            "follower_count": 4200,
            "video_count": 2,
        }
        mock_videos.return_value = {
            "videos": [
                {
                    "id": "video-1",
                    "title": "First clip",
                    "video_description": "Hello",
                    "create_time": 1750000000,
                    "cover_image_url": "https://example.com/cover.jpg",
                    "view_count": 1000,
                    "like_count": 120,
                    "comment_count": 8,
                }
            ],
            "cursor": 1750000000000,
            "has_more": False,
        }

        response = await client.post(
            "/api/v1/auth/tiktok/callback",
            json={"code": "auth-code", "state": state},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "tiktok"
    assert data["videos_imported"] == 1

    social_query = select(SocialAccount).where(
        SocialAccount.user_id == user.id,
        SocialAccount.provider == providers.TIKTOK,
    )
    social = (await db.execute(social_query)).scalar_one_or_none()
    assert social is not None
    assert social.provider_user_id == "open-id-123"
    assert social.access_token == "act.token"
    assert social.refresh_token == "rft.token"
    # TikTok refresh tokens are valid for ~365 days; we track their expiry.
    assert social.refresh_token_expires_at is not None

    channel_query = select(Channel).where(
        Channel.creator_id == user.id, Channel.platform == providers.TIKTOK
    )
    channel = (await db.execute(channel_query)).scalar_one_or_none()
    assert channel is not None
    assert channel.external_id == "open-id-123"
    assert channel.title == "TikTok Creator"
    assert channel.subscriber_count == 4200
