from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.waitlist.schemas import WaitlistEntryCreate, WaitlistEntryResponse
from app.modules.waitlist.services import WaitlistService

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])

@router.post(
    "",
    response_model=WaitlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join the waitlist"
)
async def join_waitlist(
    payload: WaitlistEntryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Try to resolve user's real IP address from proxy headers if behind load balancers
    ip_address = request.headers.get("x-forwarded-for")
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    entry = await WaitlistService.create_entry(
        db=db,
        email=payload.email,
        ip_address=ip_address
    )
    return entry

@router.get(
    "/count",
    summary="Get total waitlist signup count"
)
async def get_waitlist_count(db: AsyncSession = Depends(get_db)):
    count = await WaitlistService.get_count(db)
    return {"count": count}
