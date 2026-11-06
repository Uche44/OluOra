import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.core.config import settings
from app.core.security import create_access_token
from app.integrations.scrapecreators import (
    normalize_comments,
    next_cursor,
)
from app.modules.comments.models import Comment
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio


def _comment(cid: str, nickname: str = "Alice", likes: int = 3, create_time: int = 1737679448) -> dict:
    return {
        "cid": cid,
        "text": f"comment {cid}",
        "create_time": create_time,
        "digg_count": likes,
        "reply_id": "0",
        "reply_comment_total": 0,
        "user": {
            "nickname": nickname,
            "unique_id": nickname.lower(),
            "avatar_thumb": {"url_list": ["https://example.com/avatar.jpg"]},
        },
    }


def _payload(comments: list[dict], cursor: int = 20, has_more: int = 0) -> dict:
    return {
        "success": True,
        "credits_charged": 1,
        "comments": comments,
        "cursor": cursor,
        "has_more": has_more,
        "total": len(comments),
    }


async def _make_tiktok_video(
    db: AsyncSession,
    email: str,
    url: str | None = "https://www.tiktok.com/@creator/video/123",
):
    user = User(email=email, full_name="TikTok Creator", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    channel = Channel(
        creator_id=user.id,
        platform=providers.TIKTOK,
        external_id=f"open-{email}",
        title="TikTok Channel",
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    video = Video(
        channel_id=channel.id,
        platform=providers.TIKTOK,
        external_id=f"vid-{email}",
        title="TikTok video",
        url=url,
        published_at=datetime.now(timezone.utc),
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return user, channel, video


async def test_normalize_comments_maps_provider_fields():
    comments = normalize_comments(_payload([_comment("c1", nickname="Bob", likes=1015)]))

    assert len(comments) == 1
    comment = comments[0]
    assert comment.external_id == "c1"
    assert comment.author_name == "Bob"
    assert comment.author_profile_image == "https://example.com/avatar.jpg"
    assert comment.text == "comment c1"
    assert comment.like_count == 1015
    assert comment.published_at == datetime.fromtimestamp(1737679448, tz=timezone.utc)


async def test_normalize_comments_skips_incomplete_rows():
    payload = _payload([_comment("c1"), {"text": "no id"}, {"cid": "c3"}])

    comments = normalize_comments(payload)

    assert [c.external_id for c in comments] == ["c1"]


async def test_next_cursor_only_when_more_pages():
    assert next_cursor(_payload([], cursor=111, has_more=1)) == 111
    assert next_cursor(_payload([], cursor=111, has_more=0)) is None


async def test_sync_tiktok_comments_stores_and_dedupes(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "SCRAPECREATORS_API_KEY", "test-key")
    user, _, video = await _make_tiktok_video(db, "tt_comments@example.com")
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    with patch(
        "app.integrations.scrapecreators.fetch_video_comments", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = _payload([_comment("c1"), _comment("c2", nickname="Bob")])
        response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["synced_count"] == 2

        # Re-running over the same page must not duplicate rows, but should refresh likes.
        mock_fetch.return_value = _payload([_comment("c1", likes=99), _comment("c2", nickname="Bob")])
        second = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)

        assert second.status_code == 200
        assert second.json()["data"]["synced_count"] == 0

        assert mock_fetch.call_args.args[0] == video.url

    stored = (
        await db.execute(
            select(Comment).where(Comment.video_id == video.id).order_by(Comment.external_id)
        )
    ).scalars().all()
    assert [c.external_id for c in stored] == ["c1", "c2"]
    assert stored[0].like_count == 99
    assert stored[0].author_name == "Alice"

    await db.refresh(video)
    assert video.sync_status == "synced"
    assert video.last_synced_at is not None


async def test_sync_tiktok_comments_paginates(client: AsyncClient, db: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "SCRAPECREATORS_API_KEY", "test-key")
    user, _, video = await _make_tiktok_video(db, "tt_pages@example.com")
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    with patch(
        "app.integrations.scrapecreators.fetch_video_comments", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = [
            _payload([_comment("p1")], cursor=111, has_more=1),
            _payload([_comment("p2")], cursor=222, has_more=0),
        ]

        response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["synced_count"] == 2
    assert mock_fetch.call_count == 2
    assert mock_fetch.call_args_list[0].kwargs["cursor"] is None
    assert mock_fetch.call_args_list[1].kwargs["cursor"] == 111


async def test_sync_tiktok_comments_requires_video_url(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "SCRAPECREATORS_API_KEY", "test-key")
    user, _, video = await _make_tiktok_video(db, "tt_no_url@example.com", url=None)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VIDEO_URL_MISSING"


async def test_sync_tiktok_comments_disabled_without_provider_key(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "SCRAPECREATORS_API_KEY", "")
    user, _, video = await _make_tiktok_video(db, "tt_unconfigured@example.com")
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    response = await client.post(f"/api/v1/videos/{video.id}/comments/sync", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "COMMENTS_NOT_SUPPORTED"
