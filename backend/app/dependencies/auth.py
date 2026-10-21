import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_token
from app.modules.users.models import User

# HTTPBearer extracts Authorization: Bearer <token> automatically
security_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency injection helper to validate JWT tokens and resolve the current active creator user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cast user_id string to UUID to prevent PostgreSQL type mapping query errors
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
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
        
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that allows only internal admin users through.

    Reuses ``get_current_user`` (which loads the user from the DB every request),
    so admin status is checked against live data — revoking admin access takes
    effect immediately with no token reissue.

    Returns 403 (not 401) for authenticated non-admins so callers can tell
    "not logged in" apart from "logged in but not authorized".
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Admin access required.",
            },
        )
    return current_user


def can_connect_tiktok(user: User) -> bool:
    """True if the user's email is on the TikTok-beta allowlist."""
    return user.email.lower() in settings.tiktok_beta_emails_list


async def require_tiktok_beta(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow only allowlisted users through to the TikTok connect endpoints.

    Returns 403 (not 401) for authenticated non-allowlisted users so callers can
    tell "not logged in" apart from "this integration isn't available to you".
    """
    if not can_connect_tiktok(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TIKTOK_NOT_AVAILABLE",
                "message": "TikTok connection is not available for your account.",
            },
        )
    return current_user
