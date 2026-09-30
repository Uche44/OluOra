from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import require_admin
from app.modules.admin import schemas, services
from app.modules.users.models import User

# Router-level dependency: every route below requires an authenticated admin.
# Adding a new endpoint here is protected by default.
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/me", response_model=schemas.AdminIdentity, summary="Current admin identity")
async def admin_me(current_user: User = Depends(require_admin)):
    """Cheap probe the admin client uses to verify the signed-in user is an admin."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }


@router.get("/overview", response_model=schemas.OverviewResponse, summary="Top-line platform metrics")
async def admin_overview(db: AsyncSession = Depends(get_db)):
    return await services.get_overview(db)


@router.get("/growth", response_model=schemas.GrowthResponse, summary="Daily growth time-series")
async def admin_growth(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_growth(db, days)


@router.get("/funnel", response_model=schemas.FunnelResponse, summary="Activation funnel")
async def admin_funnel(db: AsyncSession = Depends(get_db)):
    return await services.get_funnel(db)


@router.get("/usage", response_model=schemas.UsageResponse, summary="External API usage")
async def admin_usage(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_usage(db, days)


@router.get("/jobs", response_model=schemas.JobsResponse, summary="Analysis job health")
async def admin_jobs(
    failure_limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_jobs(db, failure_limit)


@router.get("/users", response_model=schemas.PaginatedUsers, summary="List users")
async def admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    plan: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await services.list_users(db, page, limit, search, plan, is_active)


@router.get("/waitlist", response_model=schemas.PaginatedWaitlist, summary="List waitlist entries")
async def admin_waitlist(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await services.list_waitlist(db, page, limit, search)
