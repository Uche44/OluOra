import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminIdentity(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None


class OverviewResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    new_users_7d: int
    new_users_30d: int
    plan_split: dict[str, int]
    waitlist_total: int
    waitlist_7d: int
    waitlist_30d: int
    total_channels: int
    channels_by_platform: dict[str, int]
    total_videos: int
    total_comments: int
    total_analyses: int
    total_insights: int
    connected_accounts: dict[str, int]


class GrowthPoint(BaseModel):
    date: date
    users: int
    waitlist: int
    comments: int
    analyses: int
    insights: int


class GrowthResponse(BaseModel):
    days: int
    points: list[GrowthPoint]


class FunnelStep(BaseModel):
    key: str
    label: str
    count: int
    conversion_from_previous: float | None = None
    conversion_from_start: float


class FunnelResponse(BaseModel):
    steps: list[FunnelStep]


class EndpointUsage(BaseModel):
    endpoint: str
    units: int


class TopConsumer(BaseModel):
    user_id: uuid.UUID
    email: str
    units: int


class UsagePoint(BaseModel):
    date: date
    units: int


class UsageResponse(BaseModel):
    days: int
    units_today: int
    units_window: int
    by_endpoint: list[EndpointUsage]
    series: list[UsagePoint]
    top_consumers: list[TopConsumer]


class FailedJob(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    user_id: uuid.UUID
    attempts: int
    max_attempts: int
    last_error: str | None = None
    created_at: datetime


class JobsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    success_rate: float
    avg_duration_seconds: float | None = None
    recent_failures: list[FailedJob]


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    plan: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    connections: int
    videos: int


class PaginatedUsers(BaseModel):
    data: list[AdminUserRow]
    pagination: PaginationMeta


class WaitlistRow(BaseModel):
    id: uuid.UUID
    email: EmailStr
    source: str
    created_at: datetime
    ip_address: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedWaitlist(BaseModel):
    data: list[WaitlistRow]
    pagination: PaginationMeta
