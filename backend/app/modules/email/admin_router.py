"""Admin email endpoints: send log, batch history, and the two bulk senders.

Every route is guarded by ``require_admin`` at the router level (same guarantee
as the rest of ``/admin/*``). Both bulk endpoints support ``dry_run`` so an admin
can see the recipient count before anything is sent.
"""

import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.dependencies.auth import require_admin
from app.modules.email import schemas
from app.modules.email.services import EmailService
from app.modules.email.tasks import (
    send_feedback_reminders_task,
    send_waitlist_broadcast_task,
)
from app.modules.users.models import User

router = APIRouter(prefix="/admin/email", tags=["Admin"], dependencies=[Depends(require_admin)])

_FEEDBACK_REMINDER_SUBJECT = "How's OluOra going?"


def _paragraphs(body: str) -> list[str]:
    """Split an admin-composed body into paragraphs on blank lines."""
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def _capped_limit(requested: int | None) -> int:
    """Never exceed the per-run cap, so a single blast can't blow the daily quota."""
    if requested is None:
        return settings.EMAIL_BULK_MAX_PER_RUN
    return min(requested, settings.EMAIL_BULK_MAX_PER_RUN)


@router.get("/messages", response_model=schemas.PaginatedEmailMessages, summary="List sent emails")
async def admin_email_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await EmailService.list_messages(
        db, page=page, limit=limit, category=category, status=status, search=search
    )


@router.get("/batches", response_model=list[schemas.EmailBatchRow], summary="List bulk send batches")
async def admin_email_batches(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await EmailService.list_batches(db, limit=limit)


@router.post(
    "/feedback-reminders",
    response_model=schemas.QueueResponse,
    summary="Send feedback reminders to eligible users",
)
async def admin_feedback_reminders(
    payload: schemas.FeedbackReminderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    min_age_days = (
        payload.min_age_days
        if payload.min_age_days is not None
        else settings.FEEDBACK_REMINDER_MIN_AGE_DAYS
    )
    cooldown_days = settings.FEEDBACK_REMINDER_COOLDOWN_DAYS
    limit = _capped_limit(payload.limit)

    recipients = await EmailService.feedback_recipients(
        db, min_age_days=min_age_days, cooldown_days=cooldown_days, limit=limit
    )

    if payload.dry_run:
        return {"dry_run": True, "recipients": len(recipients), "queued": 0, "batch_id": None}

    batch = await EmailService.create_batch(
        db,
        category="feedback_reminder",
        subject=_FEEDBACK_REMINDER_SUBJECT,
        requested_by=current_user.id,
        total=len(recipients),
    )
    background_tasks.add_task(
        send_feedback_reminders_task,
        batch.id,
        min_age_days=min_age_days,
        cooldown_days=cooldown_days,
        limit=limit,
    )
    return {"dry_run": False, "recipients": len(recipients), "queued": len(recipients), "batch_id": batch.id}


@router.post(
    "/waitlist-broadcast",
    response_model=schemas.QueueResponse,
    summary="Send a broadcast to the waitlist",
)
async def admin_waitlist_broadcast(
    payload: schemas.WaitlistBroadcastRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    limit = _capped_limit(payload.limit)

    recipients = await EmailService.waitlist_recipients(
        db, limit=limit, include_existing_users=payload.include_existing_users
    )

    if payload.dry_run:
        return {"dry_run": True, "recipients": len(recipients), "queued": 0, "batch_id": None}

    batch = await EmailService.create_batch(
        db,
        category="waitlist_broadcast",
        subject=payload.subject,
        requested_by=current_user.id,
        total=len(recipients),
    )
    background_tasks.add_task(
        send_waitlist_broadcast_task,
        batch.id,
        subject=payload.subject,
        heading=payload.heading or payload.subject,
        paragraphs=_paragraphs(payload.body),
        include_existing_users=payload.include_existing_users,
        limit=limit,
    )
    return {"dry_run": False, "recipients": len(recipients), "queued": len(recipients), "batch_id": batch.id}
