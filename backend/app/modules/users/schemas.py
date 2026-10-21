import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, HttpUrl, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    profile_picture: str | None = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    full_name: str | None = None
    profile_picture: str | None = None
    is_active: bool | None = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SocialAccountBase(BaseModel):
    provider: str = "google"
    provider_user_id: str

class SocialAccountResponse(SocialAccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    token_expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectedChannelSchema(BaseModel):
    id: uuid.UUID
    platform: str
    external_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int
    video_count: int

    model_config = ConfigDict(from_attributes=True)


class ConnectedAccountSchema(BaseModel):
    provider: str
    provider_user_id: str
    token_expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    profile_picture: str | None = None
    is_active: bool
    auth_provider: str = "google"
    can_connect_tiktok: bool = False
    created_at: datetime
    connections: list[ConnectedAccountSchema] = []
    channels: list[ConnectedChannelSchema] = []

    model_config = ConfigDict(from_attributes=True)


class DashboardMetricSchema(BaseModel):
    label: str
    value: str


class DashboardActionSchema(BaseModel):
    id: uuid.UUID
    type: str  # alert, trend, opt
    title: str
    description: str
    buttonText: str


class DashboardStatsResponse(BaseModel):
    videos_analyzed: int
    comments_processed: int
    questions_discovered: int
    sentiment_score: int
    growth_score: int
    summary_title: str
    summary_content: str
    summary_date: str
    summary_metrics: list[DashboardMetricSchema] = []
    recent_actions: list[DashboardActionSchema] = []


