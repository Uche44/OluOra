"""ScrapeCreators client for TikTok comment ingestion.

TikTok's Display API exposes no comment-read endpoint to standard apps, and the
Research API is restricted to non-commercial academic use. OluOra therefore
sources public TikTok comments from ScrapeCreators (https://scrapecreators.com),
a third-party public-data provider. See ``docs/references.md``.

Billing: ScrapeCreators charges per *request* (1 credit), and each request
returns one page of top-level comments. Replies live behind a separate endpoint.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

COMMENTS_PATH = "/v1/tiktok/video/comments"


class ScrapeCreatorsError(Exception):
    """Raised when the comment provider rejects a request."""


@dataclass(frozen=True)
class NormalizedComment:
    """A provider-shaped comment reduced to the fields OluOra stores."""
    external_id: str
    author_name: str
    author_profile_image: str | None
    text: str
    like_count: int
    published_at: datetime


def is_configured() -> bool:
    return bool(settings.SCRAPECREATORS_API_KEY)


def _parse_create_time(value) -> datetime:
    """TikTok ``create_time`` is a UTC unix epoch in seconds."""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


def _avatar_url(user: dict) -> str | None:
    thumb = user.get("avatar_thumb") or {}
    urls = thumb.get("url_list") or []
    if urls:
        return urls[0]
    return user.get("avatar_url")


def normalize_comments(payload: dict) -> list[NormalizedComment]:
    """Map a raw ScrapeCreators response into normalized comments.

    Comments without an id or text are skipped rather than failing the whole page.
    """
    normalized: list[NormalizedComment] = []
    for item in payload.get("comments") or []:
        comment_id = item.get("cid") or item.get("id")
        text = item.get("text")
        if not comment_id or text is None:
            continue

        user = item.get("user") or {}
        author_name = user.get("nickname") or user.get("unique_id") or "Unknown"

        normalized.append(
            NormalizedComment(
                external_id=str(comment_id),
                author_name=str(author_name)[:255],
                author_profile_image=_avatar_url(user),
                text=str(text),
                like_count=int(item.get("digg_count") or 0),
                published_at=_parse_create_time(item.get("create_time")),
            )
        )
    return normalized


def next_cursor(payload: dict) -> int | None:
    """Return the cursor for the next page, or ``None`` when the thread is exhausted."""
    if not payload.get("has_more"):
        return None
    cursor = payload.get("cursor")
    return int(cursor) if cursor is not None else None


async def fetch_video_comments(video_url: str, cursor: int | None = None) -> dict:
    """Fetch one page of a TikTok video's top-level public comments."""
    if not is_configured():
        raise ScrapeCreatorsError("SCRAPECREATORS_NOT_CONFIGURED")

    params = {"url": video_url}
    if cursor is not None:
        params["cursor"] = cursor

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.SCRAPECREATORS_BASE_URL}{COMMENTS_PATH}",
            params=params,
            headers={"x-api-key": settings.SCRAPECREATORS_API_KEY},
        )

    if response.status_code == 401:
        raise ScrapeCreatorsError("ScrapeCreators rejected the API key")
    if response.status_code == 402:
        raise ScrapeCreatorsError("ScrapeCreators credits are exhausted")
    if response.status_code != 200:
        logger.error(
            f"ScrapeCreators comments request failed: {response.status_code} - {response.text[:200]}"
        )
        raise ScrapeCreatorsError("Failed to fetch TikTok comments")

    return response.json()
