from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.feedback.schemas import FeedbackCreate, FeedbackResponse
from app.modules.feedback.services import FeedbackService
from app.modules.users.models import User

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FeedbackService.create(
        db,
        user=current_user,
        rating=payload.rating,
        category=payload.category,
        message=payload.message,
        page=payload.page,
    )
