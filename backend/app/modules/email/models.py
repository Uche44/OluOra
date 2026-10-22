"""Persistence for outbound email: a per-message log and per-batch progress.

The log is the audit trail and the dedupe source for reminders — it answers
"did we already email this person?" without a separate bookkeeping table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmailMessage(Base):
    """One outbound email (or one attempted send)."""

    __tablename__ = "email_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Null for waitlist recipients (no account) and keeps the row if a user is deleted.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # signup_welcome | feedback_reminder | waitlist_welcome | waitlist_broadcast
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # queued | sent | skipped | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Truncated provider error. Never contains secrets.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailMessage {self.category} {self.to_email} {self.status}>"


class EmailBatch(Base):
    """A single bulk-send operation (feedback reminders, waitlist broadcast)."""

    __tablename__ = "email_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Admin who triggered the batch; null for the internal cron endpoint.
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # running | completed
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailBatch {self.category} {self.status} {self.sent}/{self.total}>"
