"""Internal endpoint for an external scheduler (Railway cron, GitHub Actions…).

Disabled unless ``INTERNAL_CRON_SECRET`` is set, and authenticated with a
constant-time comparison against the ``X-Internal-Secret`` header.
"""

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.modules.email import schemas
from app.modules.email.services import EmailService
from app.modules.email.tasks import send_feedback_reminders_task

router = APIRouter(prefix="/internal/email", tags=["Internal"])

_FEEDBACK_REMINDER_SUBJECT = "How's OluOra going?"


@router.post(
    "/run",
    response_model=schemas.QueueResponse,
    summary="Run due email jobs (external cron)",
)
async def run_due_emails(
    background_tasks: BackgroundTasks,
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    configured = settings.INTERNAL_CRON_SECRET
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DISABLED",
                "message": "Internal cron endpoint is disabled (INTERNAL_CRON_SECRET not set).",
            },
        )
    if not x_internal_secret or not secrets.compare_digest(x_internal_secret, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid internal secret."},
        )

    min_age_days = settings.FEEDBACK_REMINDER_MIN_AGE_DAYS
    cooldown_days = settings.FEEDBACK_REMINDER_COOLDOWN_DAYS
    limit = settings.EMAIL_BULK_MAX_PER_RUN

    recipients = await EmailService.feedback_recipients(
        db, min_age_days=min_age_days, cooldown_days=cooldown_days, limit=limit
    )

    if not recipients:
        return {"dry_run": False, "recipients": 0, "queued": 0, "batch_id": None}

    batch = await EmailService.create_batch(
        db,
        category="feedback_reminder",
        subject=_FEEDBACK_REMINDER_SUBJECT,
        requested_by=None,
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
