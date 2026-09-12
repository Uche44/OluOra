import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.modules.tiktok.services import sync_tiktok_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tiktok", tags=["TikTok"])


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="Sync TikTok profile and video catalog"
)
async def sync_videos(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Imports or updates the creator's TikTok profile and public video catalog."""
    try:
        videos_imported = await sync_tiktok_data(db, current_user, max_videos=limit)
        return {"videos_imported": videos_imported}
    except ValueError as e:
        if str(e) == "ACCOUNT_NOT_CONNECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ACCOUNT_NOT_CONNECTED",
                    "message": "No connected TikTok account found. Please connect your TikTok profile."
                }
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
