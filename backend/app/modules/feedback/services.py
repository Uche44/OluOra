from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feedback.models import Feedback
from app.modules.users.models import User


class FeedbackService:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user: User,
        rating: int | None,
        category: str,
        message: str,
        page: str | None = None,
    ) -> Feedback:
        entry = Feedback(
            user_id=user.id,
            email=user.email,
            rating=rating,
            category=category,
            message=message.strip(),
            page=page,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry
