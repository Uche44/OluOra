import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_get_me_success(client: AsyncClient, db: AsyncSession):
    # Create user
    user = User(email="test_settings_user@gmail.com", full_name="Settings User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create social connection
    social = SocialAccount(
        user_id=user.id,
        provider="google",
        provider_user_id="google-id-12345",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(social)

    # Create connected channel
    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_settings_channel",
        title="Settings Channel",
        subscriber_count=1000,
        video_count=10
    )
    db.add(channel)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_settings_user@gmail.com"
    assert data["full_name"] == "Settings User"
    assert len(data["connections"]) == 1
    assert data["connections"][0]["provider"] == "google"
    assert len(data["channels"]) == 1
    assert data["channels"][0]["title"] == "Settings Channel"


async def test_update_me(client: AsyncClient, db: AsyncSession):
    # Create user
    user = User(email="test_update_user@gmail.com", full_name="Original Name", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Update name
    payload = {"full_name": "Updated Name"}
    response = await client.put("/api/v1/users/me", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"

    # Verify db updated
    await db.refresh(user)
    assert user.full_name == "Updated Name"


async def test_disconnect_provider_success(client: AsyncClient, db: AsyncSession):
    # Create user
    user = User(email="disconnect_user@gmail.com", full_name="Disconnect User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create social connection
    social = SocialAccount(
        user_id=user.id,
        provider="google",
        provider_user_id="google-id-disconnect",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(social)

    # Create connected channel
    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_disconnect_channel",
        title="Disconnect Channel",
        subscriber_count=1000,
        video_count=10
    )
    db.add(channel)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Disconnect
    response = await client.post("/api/v1/users/disconnect/google", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify DB cleanup
    social_query = select(SocialAccount).where(SocialAccount.user_id == user.id)
    social_res = await db.execute(social_query)
    assert social_res.scalar_one_or_none() is None

    channel_query = select(Channel).where(Channel.creator_id == user.id)
    channel_res = await db.execute(channel_query)
    assert len(channel_res.scalars().all()) == 0


async def test_disconnect_provider_not_found(client: AsyncClient, db: AsyncSession):
    user = User(email="disconnect_not_found@gmail.com", full_name="User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/users/disconnect/google", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CONNECTION_NOT_FOUND"


async def test_get_dashboard_stats(client: AsyncClient, db: AsyncSession):
    user = User(email="dash_test@gmail.com", full_name="Dash User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/users/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "videos_analyzed" in data
    assert "comments_processed" in data
    assert "questions_discovered" in data
    assert "sentiment_score" in data
    assert "growth_score" in data

