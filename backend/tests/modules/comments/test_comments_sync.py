import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.comments.services import sync_comments_for_video

pytestmark = pytest.mark.asyncio

@patch("app.integrations.youtube.fetch_comment_threads", new_callable=AsyncMock)
async def test_sync_comments_success(mock_fetch, db: AsyncSession):
    # 1. Setup creator, channel, and video
    user = User(email="test_sync@gmail.com", full_name="Sync Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_test_sync",
        title="Sync Tester Channel",
        subscriber_count=100,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-123",
        title="Testing Comment Retrieval",
        published_at=datetime.now(timezone.utc) - timedelta(days=1),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # 2. Setup mock response from YouTube API (1 thread with 1 reply)
    mock_fetch.return_value = {
        "items": [
            {
                "id": "thread-001",
                "snippet": {
                    "videoId": "video-123",
                    "topLevelComment": {
                        "id": "comment-parent-001",
                        "snippet": {
                            "authorDisplayName": "Top Level Commenter",
                            "authorProfileImageUrl": "http://img.com/avatar1.jpg",
                            "textDisplay": "Excellent video tutorial!",
                            "likeCount": 10,
                            "publishedAt": "2026-07-07T12:00:00Z"
                        }
                    }
                },
                "replies": {
                    "comments": [
                        {
                            "id": "comment-reply-001",
                            "snippet": {
                                "authorDisplayName": "Reply Commenter",
                                "authorProfileImageUrl": "http://img.com/avatar2.jpg",
                                "textDisplay": "Agreed, really helped.",
                                "likeCount": 2,
                                "publishedAt": "2026-07-07T12:15:00Z",
                                "parentId": "comment-parent-001"
                            }
                        }
                    ]
                }
            }
        ]
    }

    # 3. Trigger sync
    new_count = await sync_comments_for_video(db, video, "fake-access-token")
    assert new_count == 2

    # 4. Verify Database
    comments_stmt = select(Comment).where(Comment.video_id == video.id).order_by(Comment.published_at.asc())
    comments_res = await db.execute(comments_stmt)
    comments = comments_res.scalars().all()
    
    assert len(comments) == 2
    
    # Parent comment checks
    parent = comments[0]
    assert parent.youtube_comment_id == "comment-parent-001"
    assert parent.author_name == "Top Level Commenter"
    assert parent.text == "Excellent video tutorial!"
    assert parent.parent_id is None
    
    # Reply comment checks
    reply = comments[1]
    assert reply.youtube_comment_id == "comment-reply-001"
    assert reply.author_name == "Reply Commenter"
    assert reply.text == "Agreed, really helped."
    assert reply.parent_id == parent.id

    # Video status checks
    await db.refresh(video)
    assert video.sync_status == "completed"
    assert video.last_synced_at is not None


@patch("app.integrations.youtube.fetch_comment_threads", new_callable=AsyncMock)
async def test_sync_comments_delta_fetching(mock_fetch, db: AsyncSession):
    # Setup video
    user = User(email="test_delta@gmail.com", full_name="Delta Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_test_delta",
        title="Delta Channel",
        subscriber_count=50,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-delta",
        title="Testing Delta Sync",
        published_at=datetime.now(timezone.utc) - timedelta(days=2),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Put a comment in the DB to act as the watermark/cursor
    existing_comment = Comment(
        video_id=video.id,
        youtube_comment_id="comment-old-111",
        author_name="Old Poster",
        text="This is an old comment.",
        published_at=datetime.fromisoformat("2026-07-06T10:00:00+00:00")
    )
    db.add(existing_comment)
    await db.commit()

    # Setup mock response: returns 1 new comment (published after) and 1 old comment (published before/equal)
    mock_fetch.return_value = {
        "items": [
            {
                "id": "thread-new",
                "snippet": {
                    "videoId": "video-delta",
                    "topLevelComment": {
                        "id": "comment-new-222",
                        "snippet": {
                            "authorDisplayName": "New Poster",
                            "authorProfileImageUrl": "http://img.com/avatar3.jpg",
                            "textDisplay": "This is a new comment!",
                            "likeCount": 1,
                            "publishedAt": "2026-07-07T08:00:00Z"
                        }
                    }
                }
            },
            {
                "id": "thread-old",
                "snippet": {
                    "videoId": "video-delta",
                    "topLevelComment": {
                        "id": "comment-old-111",
                        "snippet": {
                            "authorDisplayName": "Old Poster",
                            "authorProfileImageUrl": "http://img.com/avatar4.jpg",
                            "textDisplay": "This is an old comment.",
                            "likeCount": 5,
                            "publishedAt": "2026-07-06T10:00:00Z"
                        }
                    }
                }
            }
        ]
    }

    # Run sync
    new_count = await sync_comments_for_video(db, video, "fake-access-token")
    # Only "comment-new-222" should be added since "comment-old-111" has timestamp <= existing_comment timestamp (2026-07-06 10:00:00)
    assert new_count == 1

    # Verify database has total 2 comments
    comments_stmt = select(Comment).where(Comment.video_id == video.id)
    comments_res = await db.execute(comments_stmt)
    all_comments = comments_res.scalars().all()
    assert len(all_comments) == 2


@patch("app.integrations.youtube.fetch_comment_threads", new_callable=AsyncMock)
async def test_sync_comments_disabled(mock_fetch, db: AsyncSession):
    # Setup video
    user = User(email="test_disabled@gmail.com", full_name="Disabled Tester", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        youtube_channel_id="UC_test_disabled",
        title="Disabled Channel",
        subscriber_count=10,
        video_count=1
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        youtube_video_id="video-disabled",
        title="Testing Disabled Comments",
        published_at=datetime.now(timezone.utc) - timedelta(days=2),
        sync_status="pending"
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Mock raises COMMENTS_DISABLED Exception
    mock_fetch.side_effect = Exception("COMMENTS_DISABLED")

    # Run sync
    new_count = await sync_comments_for_video(db, video, "fake-access-token")
    assert new_count == 0

    await db.refresh(video)
    assert video.sync_status == "disabled"
