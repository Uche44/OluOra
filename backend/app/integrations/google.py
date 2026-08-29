import secrets
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import jwt
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# OAuth state token lifetime. Kept short: state is a login-CSRF guard, not a session.
OAUTH_STATE_TTL_MINUTES = 10


def create_oauth_state() -> str:
    """
    Generate a short-lived, signed random state token used to prevent login CSRF.

    The token is signed with the JWT secret and expires after OAUTH_STATE_TTL_MINUTES.
    It is passed through the Google OAuth redirect and must be echoed back by the
    client on the callback so the backend can confirm the flow was initiated by the
    same browser (and not reused/forged from another origin).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "type": "oauth_state",
        "nonce": secrets.token_urlsafe(24),
        "iat": now,
        "exp": now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_oauth_state(state: str | None) -> bool:
    """Return True if ``state`` is a valid, unexpired OAuth state token."""
    if not state:
        return False
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("type") == "oauth_state"
    except jwt.PyJWTError:
        return False


def get_google_auth_url(state: str | None = None) -> str:
    """Build the authorization URL to redirect users to Google's consent page."""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl"
    ]
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",    # Required to get the long-lived refresh token
        "prompt": "consent"          # Forces consent window to ensure refresh token is returned
    }
    if state:
        params["state"] = state
    return f"{base_url}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange the OAuth authorization code for Google access and refresh tokens."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
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
