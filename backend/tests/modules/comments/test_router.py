import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from app.modules.users.models import User, SocialAccount
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio

async def test_get_comments_list_success(client: AsyncClient, db: AsyncSession):
    # 1. Setup user, channel, video, and comments
    user = User(email="router_creator@gmail.com", full_name="Router Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_router",
        title="Router Channel",
        subscriber_count=200,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-router",
        title="Testing Router Comments",
        published_at=datetime.now(timezone.utc),
        sync_status="completed"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Add 5 comments
    for i in range(5):
        comment = Comment(
            video_id=video.id,
            youtube_comment_id=f"comment-id-{i}",
            author_name=f"Commenter {i}",
            text=f"This is comment {i}",
            like_count=i,
            published_at=datetime.now(timezone.utc) - timedelta(hours=i)
        )
        db.add(comment)
    await db.commit()

    # 2. Get comments list
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get(f"/api/v1/videos/{video.id}/comments?page=1&limit=2", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["data"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["pages"] == 3


async def test_get_comments_list_unauthorized(client: AsyncClient, db: AsyncSession):
    # Try calling without auth headers
    response = await client.get(f"/api/v1/videos/{uuid.uuid4()}/comments")
    assert response.status_code == 401


async def test_get_comments_list_not_found(client: AsyncClient, db: AsyncSession):
    # Create a user
    user = User(email="other_router_user@gmail.com", full_name="Other Router User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Request comments for a random UUID video which does not exist
    response = await client.get(f"/api/v1/videos/{uuid.uuid4()}/comments", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "VIDEO_NOT_FOUND"


@patch("app.modules.comments.router.get_or_refresh_google_token", new_callable=AsyncMock)
@patch("app.modules.comments.router.sync_comments_for_video", new_callable=AsyncMock)
async def test_sync_comments_endpoint_success(mock_sync, mock_refresh, client: AsyncClient, db: AsyncSession):
    # 1. Setup user, channel, video, and social connection
    user = User(email="sync_router@gmail.com", full_name="Sync Router User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    social = SocialAccount(
        user_id=user.id,
        provider="google",
        provider_user_id="google-sync-router",
        access_token="valid-token",
        refresh_token="valid-refresh",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(social)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_sync_router",
        title="Sync Router Channel",
        subscriber_count=200,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-sync-router",
        title="Testing Router Comments Sync",
        published_at=datetime.now(timezone.utc),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # 2. Setup mocks
    mock_refresh.return_value = "refreshed-token"
    mock_sync.return_value = 8
    
    # Update video sync_status inside mock to match successful behavior
    async def mock_sync_side_effect(db_session, video_obj, token):
        video_obj.sync_status = "completed"
        return 8
    mock_sync.side_effect = mock_sync_side_effect

    # 3. Call endpoint
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["data"]["synced_count"] == 8
    assert data["data"]["sync_status"] == "completed"


async def test_sync_comments_endpoint_no_connected_account(client: AsyncClient, db: AsyncSession):
    # Setup user with no social account connection
    user = User(email="sync_router_no_acc@gmail.com", full_name="No Account Router User", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_sync_no_acc",
        title="No Acc Channel",
        subscriber_count=20,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-sync-no-acc",
        title="Testing Sync No Acc",
        published_at=datetime.now(timezone.utc),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Call endpoint
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "ACCOUNT_NOT_CONNECTED"
