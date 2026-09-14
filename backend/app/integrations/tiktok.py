"""TikTok Login Kit + Display API helpers.

Standard (non-Research) TikTok apps can authenticate users and read their own
public video catalog, but **cannot read comments**. See ``docs/references.md``.
"""
import logging
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"

SCOPES = ["user.info.basic", "user.info.profile", "user.info.stats", "video.list"]

USER_INFO_FIELDS = ",".join([
    "open_id",
    "union_id",
    "avatar_url",
    "avatar_large_url",
    "display_name",
    "username",
    "bio_description",
    "follower_count",
    "following_count",
    "likes_count",
    "video_count",
])

VIDEO_LIST_FIELDS = ",".join([
    "id",
    "title",
    "video_description",
    "create_time",
    "cover_image_url",
    "share_url",
    "duration",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
])


def get_tiktok_auth_url(state: str | None = None) -> str:
    """Build the TikTok authorization page URL for the web Login Kit flow."""
    params = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "scope": ",".join(SCOPES),
        "response_type": "code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,
    }
    if state:
        params["state"] = state
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _raise_tiktok_display_error(payload: dict, action: str) -> None:
    """Display API responses carry a nested ``error`` object; ``code == "ok"`` means success."""
    error = payload.get("error") or {}
    code = error.get("code")
    if code and code != "ok":
        message = error.get("message") or code
        logger.error(f"TikTok {action} failed: {code} - {message}")
        raise Exception(f"TikTok {action} failed: {message}")


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange the authorization code for TikTok access/refresh tokens."""
    payload = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = response.json() if response.content else {}
        if response.status_code != 200 or data.get("error"):
            logger.error(f"TikTok token exchange failed: {response.status_code} - {data}")
            raise Exception("Failed to exchange authorization code with TikTok")
        return data


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh a TikTok access token. The response may carry a rotated refresh token."""
    payload = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = response.json() if response.content else {}
        if response.status_code != 200 or data.get("error"):
            logger.error(f"TikTok token refresh failed: {response.status_code} - {data}")
            raise Exception("Failed to refresh TikTok access token")
        return data


async def revoke_access_token(access_token: str) -> None:
    """Revoke a user's authorization so TikTok no longer lists our app."""
    payload = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "token": access_token,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            await client.post(
                REVOKE_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except Exception as e:
            # Revocation is best-effort; never block a local disconnect on it.
            logger.warning(f"TikTok token revoke failed: {e}")


async def fetch_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's profile. Fields requiring ungranted scopes are omitted."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            USER_INFO_URL, params={"fields": USER_INFO_FIELDS}, headers=headers
        )
        data = response.json() if response.content else {}
        if response.status_code != 200:
            logger.error(f"TikTok user info failed: {response.status_code} - {data}")
            raise Exception("TikTok API request failed while fetching user info")
        _raise_tiktok_display_error(data, "user info")
        return data.get("data", {}).get("user", {})


async def fetch_user_videos(access_token: str, cursor: int | None = None, max_count: int = 20) -> dict:
    """Fetch one page of the authenticated user's public videos."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body: dict = {"max_count": min(max_count, 20)}
    if cursor is not None:
        body["cursor"] = cursor

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            VIDEO_LIST_URL,
            params={"fields": VIDEO_LIST_FIELDS},
            json=body,
            headers=headers,
        )
        data = response.json() if response.content else {}
        if response.status_code != 200:
            logger.error(f"TikTok video list failed: {response.status_code} - {data}")
            raise Exception("TikTok API request failed while listing videos")
        _raise_tiktok_display_error(data, "video list")
        return data.get("data", {})
