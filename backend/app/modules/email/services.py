"""Email orchestration: render → send via the active provider → log.

Routers and background tasks call into this class only. Nothing here knows
which vendor is configured — that is resolved by ``get_email_provider``.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.email import OutboundEmail, SendResult, get_email_provider
from app.modules.email.models import EmailBatch, EmailMessage
from app.modules.email.templates import render_email
from app.modules.email.tokens import create_unsubscribe_token
from app.modules.feedback.models import Feedback
from app.modules.users.models import User
from app.modules.waitlist.models import WaitlistEntry

# Statuses that count as "we already tried to reach this person".
_ATTEMPTED_STATUSES = ("queued", "sent")

# Category for a message an admin addressed by hand (see admin_router).
ADMIN_MESSAGE_CATEGORY = "admin_message"


@dataclass(slots=True)
class DirectRecipient:
    """An address an admin typed by hand, resolved against the database.

    When the address belongs to a user or a waitlist entry we carry that
    record's id so the message gets a working unsubscribe link.
    """

    email: str
    user_id: uuid.UUID | None = None
    opt_out_scope: str | None = None
    opt_out_id: uuid.UUID | None = None


class EmailService:
    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------
    @staticmethod
    def _unsubscribe_url(scope: str, object_id: uuid.UUID, email: str) -> str:
        token = create_unsubscribe_token(scope=scope, object_id=object_id, email=email)
        base = settings.API_PUBLIC_URL.rstrip("/")
        return f"{base}/api/v1/email/unsubscribe?token={token}"

    @staticmethod
    async def send(
        db: AsyncSession,
        *,
        category: str,
        to: str,
        subject: str,
        template: str,
        context: dict | None = None,
        user_id: uuid.UUID | None = None,
        batch_id: uuid.UUID | None = None,
        opt_out_scope: str | None = None,
        opt_out_id: uuid.UUID | None = None,
    ) -> EmailMessage:
        """Render and send one email, logging the outcome. Never raises on delivery failure."""
        provider = get_email_provider()
        context = context or {}

        unsubscribe_url = None
        headers: dict[str, str] = {}
        if opt_out_scope and opt_out_id:
            unsubscribe_url = EmailService._unsubscribe_url(opt_out_scope, opt_out_id, to)
            headers = {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }

        message = EmailMessage(
            to_email=to,
            user_id=user_id,
            category=category,
            subject=subject,
            provider=provider.name,
            status="queued",
            batch_id=batch_id,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

        try:
            html, text = render_email(template, unsubscribe_url=unsubscribe_url, **context)
            result = await provider.send(
                OutboundEmail(
                    to=to,
                    subject=subject,
                    html=html,
                    text=text,
                    from_email=settings.email_from_address,
                    from_name=settings.EMAIL_FROM_NAME,
                    reply_to=settings.email_reply_to_address or None,
                    headers=headers,
                    tag=category,
                )
            )
        except Exception as exc:  # a bad template must not abort a whole batch
            result = SendResult(status="failed", provider=provider.name, error=str(exc)[:500])

        message.status = result.status
        message.provider = result.provider
        message.provider_message_id = result.provider_message_id
        message.error = result.error
        message.sent_at = datetime.now(timezone.utc) if result.status == "sent" else None
        await db.commit()
        await db.refresh(message)
        return message

    # ------------------------------------------------------------------
    # Recipient selection
    # ------------------------------------------------------------------
    @staticmethod
    async def feedback_recipients(
        db: AsyncSession,
        *,
        min_age_days: int,
        cooldown_days: int,
        limit: int,
    ) -> list[User]:
        """Active users who have never submitted feedback and were not reminded recently."""
        now = datetime.now(timezone.utc)
        eligible_before = now - timedelta(days=max(0, min_age_days))
        cooldown_cutoff = now - timedelta(days=max(0, cooldown_days))

        has_feedback = (
            select(Feedback.id).where(Feedback.user_id == User.id).exists()
        )
        reminded_recently = (
            select(EmailMessage.id)
            .where(
                EmailMessage.user_id == User.id,
                EmailMessage.category == "feedback_reminder",
                EmailMessage.status.in_(_ATTEMPTED_STATUSES),
                EmailMessage.created_at >= cooldown_cutoff,
            )
            .exists()
        )

        stmt = (
            select(User)
            .where(
                User.is_active.is_(True),
                User.email.is_not(None),
                User.email_opt_out_at.is_(None),
                User.created_at <= eligible_before,
                ~has_feedback,
                ~reminded_recently,
            )
            .order_by(User.created_at.asc())
            .limit(max(1, limit))
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def waitlist_recipients(
        db: AsyncSession,
        *,
        limit: int,
        include_existing_users: bool = False,
    ) -> list[WaitlistEntry]:
        """Waitlist entries that are not unsubscribed.

        By default people who have since created an account are skipped, since a
        "you're on the list" style broadcast is noise for them.
        """
        stmt = select(WaitlistEntry).where(WaitlistEntry.unsubscribed_at.is_(None))

        if not include_existing_users:
            is_registered = (
                select(User.id)
                .where(func.lower(User.email) == func.lower(WaitlistEntry.email))
                .exists()
            )
            stmt = stmt.where(~is_registered)

        stmt = stmt.order_by(WaitlistEntry.created_at.asc()).limit(max(1, limit))
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def resolve_recipients(
        db: AsyncSession, emails: list[str]
    ) -> tuple[list[DirectRecipient], list[str]]:
        """Resolve admin-typed addresses into sendable recipients.

        Returns ``(recipients, skipped)``. Addresses are de-duplicated
        case-insensitively and matched against users, then waitlist entries, so a
        known recipient gets a working unsubscribe link. Anyone who has already
        opted out is skipped rather than mailed, even when an admin types their
        address by hand. An address we cannot match is still sent (no opt-out
        link) since the admin addressed it deliberately.
        """
        seen: dict[str, str] = {}
        for raw in emails:
            cleaned = (raw or "").strip()
            if cleaned:
                seen.setdefault(cleaned.lower(), cleaned)

        if not seen:
            return [], []

        wanted = list(seen)

        users = (
            await db.execute(select(User).where(func.lower(User.email).in_(wanted)))
        ).scalars().all()
        users_by_email = {user.email.lower(): user for user in users}

        entries = (
            await db.execute(
                select(WaitlistEntry).where(func.lower(WaitlistEntry.email).in_(wanted))
            )
        ).scalars().all()
        entries_by_email = {entry.email.lower(): entry for entry in entries}

        recipients: list[DirectRecipient] = []
        skipped: list[str] = []

        for key, original in seen.items():
            user = users_by_email.get(key)
            entry = entries_by_email.get(key)

            # Opt-outs win over an explicit address: never mail someone who
            # unsubscribed, and tell the admin it happened.
            if user is not None and user.email_opt_out_at is not None:
                skipped.append(original)
                continue
            if user is None and entry is not None and entry.unsubscribed_at is not None:
                skipped.append(original)
                continue

            if user is not None:
                recipients.append(
                    DirectRecipient(
                        email=user.email,
                        user_id=user.id,
                        opt_out_scope="user",
                        opt_out_id=user.id,
                    )
                )
            elif entry is not None:
                recipients.append(
                    DirectRecipient(
                        email=entry.email,
                        opt_out_scope="waitlist",
                        opt_out_id=entry.id,
                    )
                )
            else:
                recipients.append(DirectRecipient(email=original))

        return recipients, skipped

    # ------------------------------------------------------------------
    # Batches
    # ------------------------------------------------------------------
    @staticmethod
    async def create_batch(
        db: AsyncSession,
        *,
        category: str,
        subject: str | None,
        requested_by: uuid.UUID | None,
        total: int,
    ) -> EmailBatch:
        batch = EmailBatch(
            category=category,
            subject=subject,
            requested_by=requested_by,
            total=total,
            status="running",
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        return batch

    @staticmethod
    async def finalize_batch(db: AsyncSession, batch: EmailBatch) -> EmailBatch:
        """Recompute the batch counters from the message log and mark it complete."""
        rows = (
            await db.execute(
                select(EmailMessage.status, func.count())
                .where(EmailMessage.batch_id == batch.id)
                .group_by(EmailMessage.status)
            )
        ).all()
        counts = {status: int(count) for status, count in rows}

        batch.sent = counts.get("sent", 0)
        batch.failed = counts.get("failed", 0)
        batch.skipped = counts.get("skipped", 0)
        batch.total = counts.get("queued", 0) + batch.sent + batch.failed + batch.skipped
        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(batch)
        return batch

    # ------------------------------------------------------------------
    # Opt-out
    # ------------------------------------------------------------------
    @staticmethod
    async def unsubscribe(
        db: AsyncSession, *, scope: str, object_id: uuid.UUID, email: str
    ) -> bool:
        """Apply an opt-out. Returns False if the record is missing or the email doesn't match."""
        now = datetime.now(timezone.utc)

        if scope == "waitlist":
            entry = await db.get(WaitlistEntry, object_id)
            if not entry or entry.email.lower() != email.lower():
                return False
            entry.unsubscribed_at = now
        elif scope == "user":
            user = await db.get(User, object_id)
            if not user or user.email.lower() != email.lower():
                return False
            user.email_opt_out_at = now
        else:
            return False

        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Admin reads
    # ------------------------------------------------------------------
    @staticmethod
    async def list_messages(
        db: AsyncSession,
        *,
        page: int,
        limit: int,
        category: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> dict:
        page = max(1, page)
        limit = max(1, min(limit, 100))

        conditions = []
        if category:
            conditions.append(EmailMessage.category == category)
        if status:
            conditions.append(EmailMessage.status == status)
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(func.lower(EmailMessage.to_email).like(like))

        count_stmt = select(func.count()).select_from(EmailMessage)
        list_stmt = select(EmailMessage)
        for condition in conditions:
            count_stmt = count_stmt.where(condition)
            list_stmt = list_stmt.where(condition)

        total = int((await db.execute(count_stmt)).scalar() or 0)
        rows = (
            (
                await db.execute(
                    list_stmt.order_by(EmailMessage.created_at.desc())
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

        return {
            "data": rows,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit else 0,
            },
        }

    @staticmethod
    async def list_batches(db: AsyncSession, *, limit: int = 20) -> list[EmailBatch]:
        stmt = (
            select(EmailBatch)
            .order_by(EmailBatch.created_at.desc())
            .limit(max(1, min(limit, 100)))
        )
        return list((await db.execute(stmt)).scalars().all())
