from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.waitlist.models import WaitlistEntry

class WaitlistService:
    @staticmethod
    async def get_count(db: AsyncSession) -> int:
        # Fetch the total number of waitlist entries
        result = await db.execute(select(WaitlistEntry))
        return len(result.scalars().all())

    @staticmethod
    async def create_entry(db: AsyncSession, email: str, ip_address: str | None = None) -> WaitlistEntry:
        # Check if email is already on the list
        query = select(WaitlistEntry).where(WaitlistEntry.email == email)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered on the waitlist."
            )

        # Create new database entry
        entry = WaitlistEntry(
            email=email,
            ip_address=ip_address,
            source="landing_page"
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)

        return entry
