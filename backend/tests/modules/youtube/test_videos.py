import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio

async def create_mock_user(db: AsyncSession, email: str, name: str) -> User:
    user = User(email=email, full_name=name, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_mock_channel(db: AsyncSession, creator_id: uuid.UUID, youtube_id: str, title: str) -> Channel:
    channel = Channel(
        creator_id=creator_id,
        external_id=youtube_id,
        title=title,
        subscriber_count=1000
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel

async def create_mock_video(
    db: AsyncSession,
    channel_id: uuid.UUID,
    youtube_id: str,
    title: str,
    desc: str,
    views: int,
    comments: int,
    status: str
) -> Video:
    video = Video(
        channel_id=channel_id,
        external_id=youtube_id,
        title=title,
        description=desc,
        published_at=datetime.now(timezone.utc),
        view_count=views,
        like_count=views // 10,
        comment_count=comments,
        sync_status=status
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video

async def test_get_videos_ownership_isolation(client: AsyncClient, db: AsyncSession):
    # Create two creators and separate video sets
    user1 = await create_mock_user(db, "creator1@gmail.com", "Creator One")
    user2 = await create_mock_user(db, "creator2@gmail.com", "Creator Two")

    channel1 = await create_mock_channel(db, user1.id, "UC_chan1", "Channel One")
    channel2 = await create_mock_channel(db, user2.id, "UC_chan2", "Channel Two")

    await create_mock_video(db, channel1.id, "v1", "User 1 Video", "Desc 1", 100, 5, "pending")
    await create_mock_video(db, channel2.id, "v2", "User 2 Video", "Desc 2", 200, 10, "pending")

    # Authenticate as Creator One
    token = create_access_token({"sub": str(user1.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/videos", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["external_id"] == "v1"
    assert data["data"][0]["title"] == "User 1 Video"
    assert data["pagination"]["total"] == 1

async def test_get_videos_search_filter(client: AsyncClient, db: AsyncSession):
    user = await create_mock_user(db, "search@gmail.com", "Search User")
    channel = await create_mock_channel(db, user.id, "UC_search", "Search Channel")

    await create_mock_video(db, channel.id, "v1", "Next.js Tutorial Complete", "Course details", 100, 5, "pending")
    await create_mock_video(db, channel.id, "v2", "FastAPI CRUD Lesson", "Python coding tutorial", 200, 10, "pending")

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Search for "Next.js"
    response = await client.get("/api/v1/videos?search=Next.js", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["external_id"] == "v1"

    # Search for "tutorial" (matches "Python coding tutorial" in desc)
    response = await client.get("/api/v1/videos?search=tutorial", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2

async def test_get_videos_status_filter(client: AsyncClient, db: AsyncSession):
    user = await create_mock_user(db, "status@gmail.com", "Status User")
    channel = await create_mock_channel(db, user.id, "UC_status", "Status Channel")

    await create_mock_video(db, channel.id, "v1", "Video One", "Desc 1", 10, 0, "completed")
    await create_mock_video(db, channel.id, "v2", "Video Two", "Desc 2", 20, 0, "pending")

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Filter for analyzed (completed)
    response = await client.get("/api/v1/videos?status=analyzed", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["external_id"] == "v1"

    # Filter for pending
    response = await client.get("/api/v1/videos?status=pending", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["external_id"] == "v2"

async def test_get_videos_sorting_and_pagination(client: AsyncClient, db: AsyncSession):
    user = await create_mock_user(db, "sort@gmail.com", "Sort User")
    channel = await create_mock_channel(db, user.id, "UC_sort", "Sort Channel")

    await create_mock_video(db, channel.id, "v1", "Video Alpha", "", 10, 100, "pending")
    await create_mock_video(db, channel.id, "v2", "Video Beta", "", 500, 10, "pending")
    await create_mock_video(db, channel.id, "v3", "Video Gamma", "", 300, 50, "pending")

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Sort by views desc
    response = await client.get("/api/v1/videos?sort=views", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["external_id"] == "v2" # 500 views
    assert data["data"][1]["external_id"] == "v3" # 300 views
    assert data["data"][2]["external_id"] == "v1" # 10 views

    # Pagination: page 1 limit 2 sorted by comments desc (v1=100, v3=50, v2=10)
    response = await client.get("/api/v1/videos?sort=comments&page=1&limit=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["external_id"] == "v1" # 100 comments
    assert data["data"][1]["external_id"] == "v3" # 50 comments
    
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["pages"] == 2


async def test_get_video_details_success(client: AsyncClient, db: AsyncSession):
    user = await create_mock_user(db, "details_creator@gmail.com", "Details Creator")
    channel = await create_mock_channel(db, user.id, "UC_details", "Details Channel")
    video = await create_mock_video(db, channel.id, "v_details", "Video Details Title", "Awesome description", 1500, 15, "completed")

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/videos/{video.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(video.id)
    assert data["title"] == "Video Details Title"
    assert data["description"] == "Awesome description"
    assert data["view_count"] == 1500
    assert data["comment_count"] == 15
    assert data["sync_status"] == "completed"


async def test_get_video_details_unauthorized(client: AsyncClient, db: AsyncSession):
    response = await client.get(f"/api/v1/videos/{uuid.uuid4()}")
    assert response.status_code == 401


async def test_get_video_details_not_found(client: AsyncClient, db: AsyncSession):
    user = await create_mock_user(db, "details_other@gmail.com", "Details Other")
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/videos/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "VIDEO_NOT_FOUND"

