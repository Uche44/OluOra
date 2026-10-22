"""Background email jobs.

Routers enqueue these via FastAPI ``BackgroundTasks`` passing only primitives;
each job opens its own session (mirroring ``run_queued_analysis_job``) so it is
independent of the request's session lifecycle.
"""

import asyncio
import logging
import uuid

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.email.models import EmailBatch
from app.modules.email.services import EmailService
from app.modules.users.models import User
from app.modules.waitlist.models import WaitlistEntry

logger = logging.getLogger(__name__)


def _first_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    parts = full_name.strip().split()
    return parts[0] if parts else None


async def _throttle() -> None:
    """Pace sends to respect the provider's rate limit."""
    per_second = max(settings.EMAIL_MAX_PER_SECOND, 0.1)
    await asyncio.sleep(1.0 / per_second)


async def send_signup_welcome_task(user_id: uuid.UUID) -> None:
    """Welcome email fired once, when a new account is created."""
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if not user or not user.email:
            return

        await EmailService.send(
            db,
            category="signup_welcome",
            to=user.email,
            subject="Welcome to OluOra",
            template="welcome_signup",
            context={
                "first_name": _first_name(user.full_name),
                "dashboard_url": f"{settings.FRONTEND_URL.rstrip('/')}/dashboard",
            },
            user_id=user.id,
        )


async def send_waitlist_welcome_task(entry_id: uuid.UUID) -> None:
    """Confirmation email fired when someone joins the waitlist."""
    async with SessionLocal() as db:
        entry = await db.get(WaitlistEntry, entry_id)
        if not entry or entry.unsubscribed_at:
            return

        await EmailService.send(
            db,
            category="waitlist_welcome",
            to=entry.email,
            subject="You're on the OluOra waitlist",
            template="waitlist_welcome",
            opt_out_scope="waitlist",
            opt_out_id=entry.id,
        )


async def send_feedback_reminders_task(
    batch_id: uuid.UUID,
    *,
    min_age_days: int,
    cooldown_days: int,
    limit: int,
) -> None:
    """Nudge eligible users to leave feedback, one email at a time."""
    async with SessionLocal() as db:
        batch = await db.get(EmailBatch, batch_id)
        if not batch:
            logger.warning("Feedback reminder batch %s not found", batch_id)
            return

        recipients = await EmailService.feedback_recipients(
            db, min_age_days=min_age_days, cooldown_days=cooldown_days, limit=limit
        )

        subject = "How's OluOra going?"
        for index, user in enumerate(recipients):
            if index:
                await _throttle()
            await EmailService.send(
                db,
                category="feedback_reminder",
                to=user.email,
                subject=subject,
                template="feedback_reminder",
                context={
                    "first_name": _first_name(user.full_name),
                    # The feedback launcher lives in the dashboard.
                    "feedback_url": f"{settings.FRONTEND_URL.rstrip('/')}/dashboard",
                },
                user_id=user.id,
                batch_id=batch.id,
                opt_out_scope="user",
                opt_out_id=user.id,
            )

        await EmailService.finalize_batch(db, batch)
        logger.info("Feedback reminder batch %s finished (%d recipients)", batch_id, len(recipients))


async def send_waitlist_broadcast_task(
    batch_id: uuid.UUID,
    *,
    subject: str,
    heading: str,
    paragraphs: list[str],
    include_existing_users: bool,
    limit: int,
) -> None:
    """Send an admin-composed broadcast to the waitlist."""
    async with SessionLocal() as db:
        batch = await db.get(EmailBatch, batch_id)
        if not batch:
            logger.warning("Waitlist broadcast batch %s not found", batch_id)
            return

        recipients = await EmailService.waitlist_recipients(
            db, limit=limit, include_existing_users=include_existing_users
        )

        for index, entry in enumerate(recipients):
            if index:
                await _throttle()
            await EmailService.send(
                db,
                category="waitlist_broadcast",
                to=entry.email,
                subject=subject,
                template="waitlist_broadcast",
                context={
                    "heading": heading,
                    "paragraphs": paragraphs,
                    "footer_note": "You're receiving this because you joined the OluOra waitlist.",
                },
                batch_id=batch.id,
                opt_out_scope="waitlist",
                opt_out_id=entry.id,
            )

        await EmailService.finalize_batch(db, batch)
        logger.info("Waitlist broadcast batch %s finished (%d recipients)", batch_id, len(recipients))
