import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, ApiQuotaUsage

# Plan limits
PLAN_LIMITS = {
    "free": 500,
    "pro": 2500
}

async def get_daily_quota_used(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Calculates total YouTube API quota units consumed by user since midnight UTC."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    stmt = (
        select(func.sum(ApiQuotaUsage.units_used))
        .where(
            ApiQuotaUsage.user_id == user_id,
            ApiQuotaUsage.called_at >= today_start
        )
    )
    result = await db.execute(stmt)
    total_used = result.scalar() or 0
    return total_used

async def verify_quota_limit(db: AsyncSession, user_id: uuid.UUID, planned_cost: int = 1) -> None:
    """
    Checks if executing a request with planned_cost will exceed the user's daily quota limit.
    Raises ValueError("QUOTA_EXCEEDED") if limits are reached.
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    plan = user.plan if user else "free"
    limit = PLAN_LIMITS.get(plan.lower(), 500)
    
    used = await get_daily_quota_used(db, user_id)
    if used + planned_cost > limit:
        raise ValueError("QUOTA_EXCEEDED")

async def log_youtube_quota(db: AsyncSession, user_id: uuid.UUID, endpoint: str, units: int) -> None:
    """Records a YouTube API call and its unit cost to the quota usage log."""
    usage = ApiQuotaUsage(
        user_id=user_id,
        endpoint=endpoint,
        units_used=units
    )
    db.add(usage)
    await db.commit()
