from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.tiktok_service import (
    exchange_code_for_token,
    get_tiktok_user,
)
from app.models.user import User
from app.models.social_account import SocialAccount
from app.core.security import create_access_token
import uuid
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/tiktok")
async def sign_in_with_tiktok(code: str, db: Session = Depends(get_db)):
    """
    Handles the TikTok OAuth flow:
    1. Exchanges the frontend code for a TikTok access token.
    2. Fetches user profile data from TikTok.
    3. Looks up the user in the database (via social_accounts).
    4. Creates a new User and SocialAccount if they don't exist.
    5. Returns a JWT access token and the user's TikTok profile info.
    """
    # 1. Exchange code for token
    token_data = await exchange_code_for_token(code)

    if "access_token" not in token_data:
        raise HTTPException(
            status_code=400, 
            detail=token_data.get("error_description", "Invalid TikTok code or OAuth error")
        )

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 0)
    token_expiry = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None

    # 2. Get TikTok user info
    user_data = await get_tiktok_user(access_token)
    
    if "data" not in user_data or "user" not in user_data["data"]:
        raise HTTPException(status_code=400, detail="Failed to fetch TikTok user info")

    tiktok_user = user_data["data"]["user"]
    platform_user_id = tiktok_user["open_id"]
    display_name = tiktok_user.get("display_name")
    username = tiktok_user.get("username")
    avatar_url = tiktok_user.get("avatar_url")

    # 3. Check if social account exists
    social_account = db.query(SocialAccount).filter(
        SocialAccount.platform == "tiktok",
        SocialAccount.platform_user_id == platform_user_id
    ).first()

    if social_account:
        # EXISTING USER → LOGIN
        user = db.query(User).filter(User.id == social_account.user_id).first()
        
        # Update tokens and username if they've changed
        social_account.access_token = access_token
        if refresh_token:
            social_account.refresh_token = refresh_token
        social_account.token_expiry = token_expiry
        if username:
            social_account.username = username
        
        db.commit()
    else:
        # NEW USER → CREATE
        user = User(id=uuid.uuid4())
        db.add(user)
        db.flush()  # Get user.id for social_account

        social_account = SocialAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            platform="tiktok",
            platform_user_id=platform_user_id,
            username=username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )
        db.add(social_account)
        db.commit()
        db.refresh(user)

    # 4. Create application JWT
    app_token = create_access_token(user.id)

    # 5. Return JSON including profile info
    return {
        "access_token": app_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "display_name": display_name,
            "username": username,
            "avatar_url": avatar_url,
            "platform": "tiktok"
        }
    }
