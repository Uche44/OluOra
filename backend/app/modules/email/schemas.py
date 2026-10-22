import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailMessageRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    to_email: str
    user_id: uuid.UUID | None = None
    category: str
    subject: str
    provider: str
    status: str
    error: str | None = None
    batch_id: uuid.UUID | None = None
    created_at: datetime
    sent_at: datetime | None = None


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class PaginatedEmailMessages(BaseModel):
    data: list[EmailMessageRow]
    pagination: PaginationMeta


class EmailBatchRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    subject: str | None = None
    requested_by: uuid.UUID | None = None
    total: int
    sent: int
    failed: int
    skipped: int
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class FeedbackReminderRequest(BaseModel):
    # Defaults come from settings when omitted.
    min_age_days: int | None = Field(None, ge=0, le=365)
    limit: int | None = Field(None, ge=1, le=1000)
    dry_run: bool = False


class WaitlistBroadcastRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    # Optional big heading; falls back to the subject when omitted.
    heading: str | None = Field(None, max_length=200)
    limit: int | None = Field(None, ge=1, le=1000)
    # Include people who have since created an account (default: skip them).
    include_existing_users: bool = False
    dry_run: bool = False
    # Addresses the admin typed by hand. When non-empty the message goes only to
    # these, and the waitlist selection (limit / include_existing_users) is ignored.
    recipients: list[EmailStr] = Field(default_factory=list, max_length=25)


class QueueResponse(BaseModel):
    dry_run: bool
    recipients: int
    queued: int
    batch_id: uuid.UUID | None = None
    # Addresses withheld because they had opted out, so the admin can see why a
    # typed-in address was not mailed.
    skipped: int = 0
    skipped_emails: list[str] = Field(default_factory=list)
