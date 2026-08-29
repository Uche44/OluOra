import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User, SocialAccount, RefreshToken
from app.core.security import create_refresh_token, decode_token
from app.integrations import google as google_integration
from app.modules.users import token_service

pytestmark = pytest.mark.asyncio

async def test_get_google_url(client: AsyncClient):
    response = await client.get("/api/v1/auth/google/url")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "accounts.google.com" in data["url"]
    assert "scope=" in data["url"]
    assert "youtube.readonly" in data["url"]
    assert "state=" in data["url"]
    assert data["state"]

async def test_google_callback_rejects_missing_state(client: AsyncClient):
    # A callback with no/invalid OAuth state must be rejected (login CSRF guard).
    payload = {"code": "google-auth-code-xyz"}
    response = await client.post("/api/v1/auth/google/callback", json=payload)
    assert response.status_code == 400

async def test_google_callback_rejects_forged_state(client: AsyncClient):
    # A tampered/forged state token must be rejected.
    payload = {"code": "google-auth-code-xyz", "state": "forged-state-token"}
    response = await client.post("/api/v1/auth/google/callback", json=payload)
    assert response.status_code == 400

@patch("app.integrations.google.exchange_code_for_tokens", new_callable=AsyncMock)
@patch("app.integrations.google.get_google_user_profile", new_callable=AsyncMock)
async def test_google_callback_new_user(
    mock_get_profile,
    mock_exchange_code,
    client: AsyncClient,
    db: AsyncSession
):
    # Setup mocks
    mock_exchange_code.return_value = {
        "access_token": "google-access-token-123",
        "refresh_token": "google-refresh-token-123",
        "expires_in": 3600
    }
    mock_get_profile.return_value = {
        "email": "creator_auth_test@gmail.com",
        "sub": "google-id-unique-789",
        "name": "Olu Creator Test",
        "picture": "https://example.com/avatar.jpg"
    }

    # Execute request
    state = google_integration.create_oauth_state()
    payload = {"code": "google-auth-code-xyz", "state": state}
    response = await client.post("/api/v1/auth/google/callback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "creator_auth_test@gmail.com"
    assert data["user"]["full_name"] == "Olu Creator Test"

    # Verify user was created in the database
    user_query = select(User).where(User.email == "creator_auth_test@gmail.com")
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    assert user is not None
    assert user.full_name == "Olu Creator Test"

    # Verify social account was created in the database
    social_query = select(SocialAccount).where(SocialAccount.user_id == user.id)
    social_result = await db.execute(social_query)
    social = social_result.scalar_one_or_none()
    assert social is not None
    assert social.provider == "google"
    assert social.provider_user_id == "google-id-unique-789"
    assert social.access_token == "google-access-token-123"
    assert social.refresh_token == "google-refresh-token-123"

@patch("app.integrations.google.exchange_code_for_tokens", new_callable=AsyncMock)
@patch("app.integrations.google.get_google_user_profile", new_callable=AsyncMock)
async def test_google_callback_existing_user(
    mock_get_profile,
    mock_exchange_code,
    client: AsyncClient,
    db: AsyncSession
):
    # 1. Pre-insert user and social account to DB
    user = User(
        email="existing_creator@gmail.com",
        full_name="Old Name",
        profile_picture="https://old-avatar.jpg",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    social = SocialAccount(
        user_id=user.id,
        provider="google",
        provider_user_id="google-id-existing-999",
        access_token="old-google-access",
        refresh_token="old-google-refresh",
        token_expires_at=user.created_at
    )
    db.add(social)
    await db.commit()

    # 2. Setup mocks with new name and updated tokens
    mock_exchange_code.return_value = {
        "access_token": "new-google-access-token",
        "refresh_token": "new-google-refresh-token",
        "expires_in": 3600
    }
    mock_get_profile.return_value = {
        "email": "existing_creator@gmail.com",
        "sub": "google-id-existing-999",
        "name": "New Name Update",
        "picture": "https://new-avatar.jpg"
    }

    # Execute callback request
    state = google_integration.create_oauth_state()
    payload = {"code": "existing-auth-code", "state": state}
    response = await client.post("/api/v1/auth/google/callback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["full_name"] == "New Name Update"

    # Verify DB user details were updated
    await db.refresh(user)
    assert user.full_name == "New Name Update"
    assert user.profile_picture == "https://new-avatar.jpg"

    # Verify DB social account tokens were updated
    await db.refresh(social)
    assert social.access_token == "new-google-access-token"
    assert social.refresh_token == "new-google-refresh-token"

async def test_refresh_token_success(client: AsyncClient, db: AsyncSession):
    # 1. Create a user
    user = User(
        email="token_refresh@gmail.com",
        full_name="Refresh Tester",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 2. Sign and persist a valid refresh token (server-side registry tracks it)
    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user.id)}, jti=refresh_jti)
    await token_service.issue_refresh_token(db, user.id, refresh_token, refresh_jti)

    # 3. Call refresh endpoint
    payload = {"refresh_token": refresh_token}
    response = await client.post("/api/v1/auth/refresh", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Decode and check that new access token belongs to user
    decoded = decode_token(data["access_token"])
    assert decoded is not None
    assert decoded["sub"] == str(user.id)
    assert decoded["type"] == "access"

    # Old token must now be revoked (rotated) server-side
    old_result = await db.execute(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    old_row = old_result.scalar_one_or_none()
    assert old_row is not None
    assert old_row.revoked is True

    # The new refresh token must also be valid for a follow-up refresh (rotation chain)
    repeated = await client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert repeated.status_code == 200

async def test_refresh_token_reuse_rejected(client: AsyncClient, db: AsyncSession):
    # Rotating a refresh token must make the ORIGINAL unusable (reuse detection).
    user = User(email="token_reuse@gmail.com", full_name="Reuse Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user.id)}, jti=refresh_jti)
    await token_service.issue_refresh_token(db, user.id, refresh_token, refresh_jti)

    # First use rotates + invalidates the token
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200

    # Replaying the SAME token must now fail
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401

async def test_logout_revokes_tokens(client: AsyncClient, db: AsyncSession):
    user = User(email="logout_tester@gmail.com", full_name="Logout Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(user.id)}, jti=refresh_jti)
    await token_service.issue_refresh_token(db, user.id, refresh_token, refresh_jti)

    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    # Logged-out token can no longer refresh
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 401

async def test_refresh_token_invalid(client: AsyncClient):
    payload = {"refresh_token": "invalid.signature.payload"}
    response = await client.post("/api/v1/auth/refresh", json=payload)
    assert response.status_code == 401
    assert "invalid or expired refresh token" in response.json()["detail"].lower()
