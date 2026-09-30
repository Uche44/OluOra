import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import providers
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token
from app.dependencies.auth import get_current_user
from app.modules.users.models import User, SocialAccount
from app.modules.users.schemas import UserResponse
from app.modules.users import token_service
from app.modules.users.social_tokens import get_social_account
from app.integrations import google, tiktok
from app.integrations.oauth_state import create_oauth_state, verify_oauth_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleLoginRequest(BaseModel):
    code: str
    state: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LogoutRequest(BaseModel):
    refresh_token: str


async def _issue_session(db: AsyncSession, user: User) -> dict:
    """Create OluOra JWTs and persist the refresh token server-side for rotation/revocation."""
    jwt_access = create_access_token({"sub": str(user.id)})
    refresh_jti = str(uuid.uuid4())
    jwt_refresh = create_refresh_token({"sub": str(user.id)}, jti=refresh_jti)
    await token_service.issue_refresh_token(db, user.id, jwt_refresh, refresh_jti)
    return {"access_token": jwt_access, "refresh_token": jwt_refresh, "user": user}


async def _upsert_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    provider_user_id: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int,
    refresh_expires_in: int | None = None,
) -> SocialAccount:
    """Create or update the user's connection for a data provider."""
    now = datetime.now(timezone.utc)
    social = await get_social_account(db, user_id, provider)
    if social is None:
        social = SocialAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=now + timedelta(seconds=expires_in),
            refresh_token_expires_at=(
                now + timedelta(seconds=refresh_expires_in) if refresh_expires_in else None
            ),
        )
    else:
        social.provider_user_id = provider_user_id
        social.access_token = access_token
        if refresh_token:
            social.refresh_token = refresh_token
        social.token_expires_at = now + timedelta(seconds=expires_in)
        if refresh_expires_in:
            social.refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)
    db.add(social)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ACCOUNT_ALREADY_CONNECTED",
                "message": f"This {provider} account is already linked to another OluOra account.",
            },
        )
    await db.refresh(social)
    return social


# ---------------------------------------------------------------------------
# Google login (identity only)
# ---------------------------------------------------------------------------

@router.get("/google/url", summary="Get Google sign-in URL")
async def get_google_url(client: str | None = None):
    """Returns the Google consent URL and a signed state token.

    The login flow requests identity scopes only; connecting YouTube is a
    separate consent handled by ``/auth/youtube/url``.

    Pass ``?client=admin`` from the isolated admin app so the browser returns to
    the admin callback. The redirect target is selected server-side from config
    (never taken from the request), so this cannot be used for open redirects.
    """
    redirect_uri = (
        settings.GOOGLE_ADMIN_REDIRECT_URI
        if client == "admin"
        else settings.GOOGLE_REDIRECT_URI
    )
    state = create_oauth_state(providers.FLOW_LOGIN, redirect_uri=redirect_uri)
    url = google.get_google_auth_url(
        state=state,
        scopes=google.LOGIN_SCOPES,
        redirect_uri=redirect_uri,
    )
    return {"url": url, "state": state}

@router.post("/google/callback", response_model=TokenResponse, summary="Process Google sign-in callback")
async def google_callback(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Processes the callback code, upserts the user account, and issues OluOra JWTs."""
    # 0. Verify the OAuth state token to prevent login CSRF (forged/reused flows).
    state_payload = verify_oauth_state(payload.state, providers.FLOW_LOGIN)
    if not state_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the sign-in flow again.",
        )

    # 1. Exchange OAuth code for Google credentials. The redirect URI must match
    # the one used to obtain the code, so it is replayed from the signed state.
    try:
        tokens = await google.exchange_code_for_tokens(
            payload.code, redirect_uri=state_payload.get("redirect_uri")
        )
    except Exception:
        logger.exception("Google token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange failed. Please try again.",
        )

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve access token from Google"
        )

    # 2. Retrieve user profile info from Google
    try:
        profile = await google.get_google_user_profile(access_token)
    except Exception:
        logger.exception("Failed to fetch Google profile")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve your Google profile. Please try again.",
        )

    email = profile.get("email")
    google_id = profile.get("sub")
    name = profile.get("name")
    picture = profile.get("picture")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile is missing email or user ID"
        )

    # 3. Create or update User record (identity lives on the user, not a social account)
    user_query = select(User).where(User.email == email)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            full_name=name,
            profile_picture=picture,
            is_active=True,
            auth_provider=providers.GOOGLE,
            auth_provider_id=google_id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created new user account: {email}")
    else:
        user.full_name = name
        user.profile_picture = picture
        user.auth_provider = providers.GOOGLE
        user.auth_provider_id = google_id
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Keep admin status in sync with the env allowlist so a newly-added admin is
    # recognized on their next login without waiting for a restart.
    desired_admin = email.lower() in settings.admin_emails_list
    if user.is_admin != desired_admin:
        user.is_admin = desired_admin
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return await _issue_session(db, user)


# ---------------------------------------------------------------------------
# YouTube connection (data provider)
# ---------------------------------------------------------------------------

@router.get("/youtube/url", summary="Get YouTube connection URL")
async def get_youtube_url(current_user: User = Depends(get_current_user)):
    """Returns the Google consent URL that grants read-only YouTube access."""
    state = create_oauth_state(providers.FLOW_YOUTUBE_CONNECT, user_id=current_user.id)
    url = google.get_google_auth_url(
        state=state,
        scopes=google.YOUTUBE_SCOPES,
        redirect_uri=settings.GOOGLE_YOUTUBE_REDIRECT_URI,
    )
    return {"url": url, "state": state}

@router.post("/youtube/callback", summary="Connect a YouTube channel")
async def youtube_callback(
    payload: GoogleLoginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchanges the consent code, stores the YouTube connection, and imports the channel."""
    state_payload = verify_oauth_state(payload.state, providers.FLOW_YOUTUBE_CONNECT)
    if not state_payload or state_payload.get("sub") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the connection flow again.",
        )

    try:
        tokens = await google.exchange_code_for_tokens(
            payload.code, redirect_uri=settings.GOOGLE_YOUTUBE_REDIRECT_URI
        )
        profile = await google.get_google_user_profile(tokens.get("access_token"))
    except Exception:
        logger.exception("YouTube connection token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to connect your YouTube account. Please try again.",
        )

    google_id = profile.get("sub")
    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile is missing a user ID",
        )

    await _upsert_connection(
        db,
        user_id=current_user.id,
        provider=providers.YOUTUBE,
        provider_user_id=google_id,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in", 3600),
    )

    # Import the channel right away so the connection is immediately useful.
    videos_imported = 0
    sync_error = None
    try:
        from app.modules.youtube.services import sync_youtube_data
        videos_imported = await sync_youtube_data(db, current_user)
    except Exception as e:
        logger.exception("Initial YouTube sync failed")
        sync_error = str(e)

    return {
        "success": True,
        "provider": providers.YOUTUBE,
        "videos_imported": videos_imported,
        "warning": sync_error,
    }


# ---------------------------------------------------------------------------
# TikTok connection (data provider)
# ---------------------------------------------------------------------------

@router.get("/tiktok/url", summary="Get TikTok connection URL")
async def get_tiktok_url(current_user: User = Depends(get_current_user)):
    """Returns the TikTok consent URL for connecting a creator's TikTok account."""
    # A blank redirect_uri still renders TikTok's consent page, but the code has
    # nowhere to come back to, so fail fast with a clear server-side log instead.
    missing = [
        name
        for name, value in (
            ("TIKTOK_CLIENT_KEY", settings.TIKTOK_CLIENT_KEY),
            ("TIKTOK_REDIRECT_URI", settings.TIKTOK_REDIRECT_URI),
        )
        if not value
    ]
    if missing:
        logger.warning(f"TikTok connect requested but not configured: missing {', '.join(missing)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PROVIDER_NOT_CONFIGURED",
                "message": "TikTok integration is not configured on this server.",
            },
        )
    state = create_oauth_state(providers.FLOW_TIKTOK_CONNECT, user_id=current_user.id)
    url = tiktok.get_tiktok_auth_url(state=state)
    return {"url": url, "state": state}

@router.post("/tiktok/callback", summary="Connect a TikTok account")
async def tiktok_callback(
    payload: GoogleLoginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchanges the consent code, stores the TikTok connection, and imports the video catalog."""
    state_payload = verify_oauth_state(payload.state, providers.FLOW_TIKTOK_CONNECT)
    if not state_payload or state_payload.get("sub") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the connection flow again.",
        )

    try:
        tokens = await tiktok.exchange_code_for_tokens(payload.code)
        user_info = await tiktok.fetch_user_info(tokens["access_token"])
    except Exception:
        logger.exception("TikTok connection token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to connect your TikTok account. Please try again.",
        )

    open_id = tokens.get("open_id") or user_info.get("open_id")
    if not open_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TikTok did not return an account identifier",
        )

    await _upsert_connection(
        db,
        user_id=current_user.id,
        provider=providers.TIKTOK,
        provider_user_id=open_id,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in", 86400),
        refresh_expires_in=tokens.get("refresh_expires_in"),
    )

    videos_imported = 0
    sync_error = None
    try:
        from app.modules.tiktok.services import sync_tiktok_data
        videos_imported = await sync_tiktok_data(db, current_user)
    except Exception as e:
        logger.exception("Initial TikTok sync failed")
        sync_error = str(e)

    return {
        "success": True,
        "provider": providers.TIKTOK,
        "videos_imported": videos_imported,
        "warning": sync_error,
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=RefreshTokenResponse, summary="Refresh OluOra JWT access token")
async def refresh_access_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Rotates a refresh token: validates the existing one, revokes it server-side,
    and issues a fresh access + refresh token pair. A stolen/used token cannot be reused."""
    # 1. Validate the presented token against the server-side registry.
    validated = await token_service.validate_refresh_token(db, payload.refresh_token)
    if not validated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    row, user = validated

    # 2. Revoke the old token (rotation), so it can never be used again.
    await token_service.revoke_refresh_token(db, row)

    # 3. Issue a fresh access token + a new refresh token, and persist the new one.
    new_access = create_access_token({"sub": str(user.id)})
    new_refresh_jti = str(uuid.uuid4())
    new_refresh = create_refresh_token({"sub": str(user.id)}, jti=new_refresh_jti)
    await token_service.issue_refresh_token(db, user.id, new_refresh, new_refresh_jti)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }

@router.post("/logout", summary="Log out and revoke refresh tokens")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    """Revokes the presented refresh token (and all others for that user)."""
    await token_service.revoke_by_token(db, payload.refresh_token)
    # Always succeed from the client's perspective; over-revoking is safe.
    return {"success": True}
