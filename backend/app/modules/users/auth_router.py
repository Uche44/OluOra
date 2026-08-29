import uuid
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token
from app.modules.users.models import User, SocialAccount
from app.modules.users.schemas import UserResponse
from app.modules.users import token_service
from app.integrations import google

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

@router.get("/google/url", summary="Get Google OAuth authorization URL")
async def get_google_url():
    """Returns the authorization redirect URI for initiating YouTube Sign-In.

    Also returns a signed, expiring `state` token that the client must store and
    echo back to the callback endpoint to guard against login CSRF.
    """
    state = google.create_oauth_state()
    url = google.get_google_auth_url(state=state)
    return {"url": url, "state": state}

@router.post("/google/callback", response_model=TokenResponse, summary="Process Google OAuth callback code")
async def google_callback(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Processes the callback code, exchanges it for tokens, syncs user records, and issues JWTs."""
    # 0. Verify the OAuth state token to prevent login CSRF (forged/reused flows).
    if not google.verify_oauth_state(payload.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the sign-in flow again.",
        )

    # 1. Exchange OAuth code for Google credentials
    try:
        tokens = await google.exchange_code_for_tokens(payload.code)
    except Exception:
        logger.exception("Google token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange failed. Please try again.",
        )
    
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    
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

    # 3. Create or update User record
    user_query = select(User).where(User.email == email)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if not user:
        # Create new User
        user = User(
            email=email,
            full_name=name,
            profile_picture=picture,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created new user account: {email}")
    else:
        # Update existing User profile
        user.full_name = name
        user.profile_picture = picture
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 4. Create or update Google SocialAccount details
    social_query = select(SocialAccount).where(SocialAccount.user_id == user.id)
    social_result = await db.execute(social_query)
    social = social_result.scalar_one_or_none()
    
    if not social:
        social = SocialAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at
        )
        db.add(social)
    else:
        social.access_token = access_token
        # Google only returns refresh_token on initial consent. Keep the old one if none is returned.
        if refresh_token:
            social.refresh_token = refresh_token
        social.token_expires_at = token_expires_at
        db.add(social)
        
    await db.commit()

    # 5. Generate OluOra JWT session tokens and persist the refresh token
    #    server-side so it can be rotated and revoked.
    jwt_access = create_access_token({"sub": str(user.id)})
    refresh_jti = str(uuid.uuid4())
    jwt_refresh = create_refresh_token({"sub": str(user.id)}, jti=refresh_jti)
    await token_service.issue_refresh_token(db, user.id, jwt_refresh, refresh_jti)

    return {
        "access_token": jwt_access,
        "refresh_token": jwt_refresh,
        "user": user
    }

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
