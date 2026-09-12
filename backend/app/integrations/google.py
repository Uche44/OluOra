"""Google OAuth helpers.

Used for two distinct flows:
  * ``login``  — identity-only scopes (openid/email/profile).
  * ``youtube_connect`` — identity scopes plus YouTube read/write scopes.
"""
import logging
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

LOGIN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

YOUTUBE_SCOPES = [
    *LOGIN_SCOPES,
    "https://www.googleapis.com/auth/youtube.readonly",
    # Required by commentThreads.list / comments.list in practice: a read-only
    # token alone is rejected with ACCESS_TOKEN_SCOPE_INSUFFICIENT (403).
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_google_auth_url(
    state: str | None = None,
    scopes: list[str] | None = None,
    redirect_uri: str | None = None,
) -> str:
    """Build the authorization URL to redirect users to Google's consent page."""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes if scopes is not None else LOGIN_SCOPES),
        "access_type": "offline",    # Required to get the long-lived refresh token
        "prompt": "consent"          # Forces consent window to ensure refresh token is returned
    }
    if state:
        params["state"] = state
    return f"{base_url}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str, redirect_uri: str | None = None) -> dict:
    """Exchange the OAuth authorization code for Google access and refresh tokens."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, data=payload)
            if response.status_code != 200:
                logger.error(f"Failed token exchange: {response.status_code} - {response.text}")
                raise Exception("Failed to exchange authorization code with Google")
            return response.json()
        except Exception as e:
            logger.error(f"Error during code exchange with Google: {e}")
            raise

async def get_google_user_profile(access_token: str) -> dict:
    """Fetch user profile information from Google UserInfo endpoint."""
    url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch profile: {response.status_code} - {response.text}")
                raise Exception("Failed to retrieve profile information from Google")
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Google UserInfo: {e}")
            raise

async def refresh_google_access_token(refresh_token: str) -> dict:
    """Refresh Google access token using a valid refresh token."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, data=payload)
            if response.status_code != 200:
                logger.error(f"Failed refreshing Google token: {response.status_code} - {response.text}")
                raise Exception("Failed to refresh Google access token")
            return response.json()
        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")
            raise
