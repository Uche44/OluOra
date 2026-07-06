import uuid
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.users.models import User, SocialAccount
from app.modules.users.schemas import UserResponse
from app.integrations import google

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleLoginRequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.get("/google/url", summary="Get Google OAuth authorization URL")
async def get_google_url():
    """Returns the authorization redirect URI for initiating YouTube Sign-In."""
    url = google.get_google_auth_url()
    return {"url": url}

@router.post("/google/callback", response_model=TokenResponse, summary="Process Google OAuth callback code")
async def google_callback(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Processes the callback code, exchanges it for tokens, syncs user records, and issues JWTs."""
    # 1. Exchange OAuth code for Google credentials
    try:
        tokens = await google.exchange_code_for_tokens(payload.code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google token exchange failed: {str(e)}"
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch Google profile: {str(e)}"
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

    # 5. Generate OluOra JWT session tokens
    jwt_access = create_access_token({"sub": str(user.id)})
    jwt_refresh = create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": jwt_access,
        "refresh_token": jwt_refresh,
        "user": user
    }

@router.post("/refresh", response_model=RefreshTokenResponse, summary="Refresh OluOra JWT access token")
async def refresh_access_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Generates a new access token using a valid OluOra JWT refresh token."""
    decoded = decode_token(payload.refresh_token)
    
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = decoded.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
        
    new_access = create_access_token({"sub": str(user.id)})
    
    return {
        "access_token": new_access
    }
