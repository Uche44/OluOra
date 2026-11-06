import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.modules.content import schemas, services
from app.modules.users.models import User

router = APIRouter(prefix="/content", tags=["Content Strategy"])


@router.get(
    "/opportunities/sources",
    response_model=schemas.AnalysisSourceListResponse,
    summary="List completed analyses available for opportunity generation",
)
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await services.list_analysis_sources(db, current_user)}


@router.post(
    "/opportunities/generate",
    response_model=schemas.GenerateOpportunitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate evidence-backed content opportunities from an analysis",
)
async def generate_opportunities(
    payload: schemas.GenerateOpportunitiesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        opportunities, cached = await services.generate_opportunities(
            db,
            current_user,
            analysis_id=payload.analysis_id,
            limit=payload.limit,
            force=payload.force,
        )
    except services.AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ANALYSIS_NOT_FOUND",
                "message": "The requested analysis does not exist or you do not have permission to view it.",
            },
        )
    except services.AnalysisNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ANALYSIS_NOT_READY",
                "message": "This analysis has not completed yet.",
            },
        )
    except services.InsufficientEvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "INSUFFICIENT_EVIDENCE", "message": str(exc)},
        )
    except services.OpportunityGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "GENERATION_FAILED", "message": str(exc)},
        )

    return {"data": opportunities, "cached": cached}


@router.get(
    "/opportunities",
    response_model=schemas.OpportunityListResponse,
    summary="List the creator's content opportunities",
)
async def list_opportunities(
    status_filter: str | None = Query(None, alias="status", pattern="^(new|saved|dismissed)$"),
    analysis_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    opportunities, total = await services.list_opportunities(
        db,
        current_user,
        status=status_filter,
        analysis_id=analysis_id,
        page=page,
        limit=limit,
    )
    pages = math.ceil(total / limit) if total else 0
    return {
        "data": opportunities,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
        },
    }


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=schemas.ContentOpportunityOut,
    summary="Get one opportunity with its evidence",
)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.get_opportunity(db, current_user, opportunity_id)
    except services.OpportunityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OPPORTUNITY_NOT_FOUND",
                "message": "The requested opportunity does not exist or you do not have permission to view it.",
            },
        )


@router.patch(
    "/opportunities/{opportunity_id}",
    response_model=schemas.ContentOpportunityOut,
    summary="Save or dismiss an opportunity",
)
async def update_opportunity(    opportunity_id: uuid.UUID,
    payload: schemas.OpportunityStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.update_opportunity_status(
            db, current_user, opportunity_id, payload.status
        )
    except services.OpportunityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OPPORTUNITY_NOT_FOUND",
                "message": "The requested opportunity does not exist or you do not have permission to modify it.",
            },
        )


# --- Weekly calendar --------------------------------------------------------


@router.get(
    "/calendar",
    response_model=schemas.CalendarWeekResponse,
    summary="Get the creator's calendar for a week",
)
async def get_calendar_week(
    week_start: date | None = Query(None, description="Any date in the target week"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    monday, sunday, data = await services.list_week_items(
        db, current_user, week_start=week_start
    )
    return {"week_start": monday, "week_end": sunday, "data": data}


@router.post(
    "/calendar/items",
    response_model=schemas.CalendarItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a calendar item (from an opportunity or manually)",
)
async def create_calendar_item(
    payload: schemas.CalendarItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.create_calendar_item(db, current_user, payload)
    except services.OpportunityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OPPORTUNITY_NOT_FOUND",
                "message": "The requested opportunity does not exist or you do not have permission to use it.",
            },
        )
    except services.InvalidCalendarRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CALENDAR_ITEM", "message": str(exc)},
        )


@router.get(
    "/calendar/items/{item_id}",
    response_model=schemas.CalendarItemOut,
    summary="Get a single calendar item",
)
async def get_calendar_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.get_calendar_item(db, current_user, item_id)
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist or you do not have permission to view it.",
            },
        )


@router.patch(
    "/calendar/items/{item_id}",
    response_model=schemas.CalendarItemOut,
    summary="Edit, move, or change the status of a calendar item",
)
async def update_calendar_item(
    item_id: uuid.UUID,
    payload: schemas.CalendarItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.update_calendar_item(db, current_user, item_id, payload)
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist or you do not have permission to modify it.",
            },
        )
    except services.InvalidCalendarRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CALENDAR_ITEM", "message": str(exc)},
        )


@router.delete(
    "/calendar/items/{item_id}",
    summary="Remove a calendar item",
)
async def delete_calendar_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await services.delete_calendar_item(db, current_user, item_id)
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist or you do not have permission to delete it.",
            },
        )
    return {"success": True}


@router.post(
    "/calendar/plan",
    response_model=schemas.CalendarPlanResponse,
    summary="Deterministically place selected opportunities into a week",
)
async def plan_calendar_week(
    payload: schemas.CalendarPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await services.plan_week(
            db,
            current_user,
            week_start=payload.week_start,
            opportunity_ids=payload.opportunity_ids,
            days=payload.days,
            platform=payload.platform,
        )
    except services.OpportunityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OPPORTUNITY_NOT_FOUND",
                "message": "One or more selected opportunities were not found.",
            },
        )
    return {"data": data, "planned": len(data)}


# --- Scripts / content briefs ----------------------------------------------


@router.get(
    "/calendar/items/{item_id}/script",
    response_model=schemas.ScriptOut,
    summary="Get the latest script for a calendar item",
)
async def get_current_script(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.get_current_script(db, current_user, item_id)
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist.",
            },
        )
    except services.ScriptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCRIPT_NOT_FOUND", "message": str(exc)},
        )


@router.get(
    "/calendar/items/{item_id}/scripts",
    response_model=schemas.ScriptListResponse,
    summary="List all script versions for a calendar item",
)
async def list_scripts(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {"data": await services.list_scripts(db, current_user, item_id)}
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist.",
            },
        )


@router.post(
    "/calendar/items/{item_id}/script/generate",
    response_model=schemas.ScriptGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a new script version for a calendar item",
)
async def generate_script(
    item_id: uuid.UUID,
    payload: schemas.ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        script, cached = await services.generate_script(
            db, current_user, item_id, force=payload.force
        )
    except services.CalendarItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CALENDAR_ITEM_NOT_FOUND",
                "message": "The requested calendar item does not exist.",
            },
        )
    except services.ScriptGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "SCRIPT_GENERATION_FAILED", "message": str(exc)},
        )
    return {"data": script, "cached": cached}


@router.get(
    "/scripts/{script_id}",
    response_model=schemas.ScriptOut,
    summary="Get a specific script version",
)
async def get_script(
    script_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.get_script(db, current_user, script_id)
    except services.ScriptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCRIPT_NOT_FOUND", "message": str(exc)},
        )


@router.patch(
    "/scripts/{script_id}",
    response_model=schemas.ScriptOut,
    summary="Edit a script version",
)
async def update_script(
    script_id: uuid.UUID,
    payload: schemas.ScriptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await services.update_script(db, current_user, script_id, payload)
    except services.ScriptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCRIPT_NOT_FOUND", "message": str(exc)},
        )
    except services.InvalidCalendarRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SCRIPT", "message": str(exc)},
        )


# --- Creator style profile ---------------------------------------------------


@router.get(
    "/style",
    response_model=schemas.StyleProfileOut,
    summary="Get the creator's manual style preferences",
)
async def get_style_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_style_profile(db, current_user)


@router.put(
    "/style",
    response_model=schemas.StyleProfileOut,
    summary="Create or update the creator's manual style preferences",
)
async def update_style_profile(
    payload: schemas.StyleProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.update_style_profile(db, current_user, payload)


