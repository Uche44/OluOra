import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ConfigDict

class ChannelBase(BaseModel):
    youtube_channel_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int = 0
    video_count: int = 0

class ChannelCreate(ChannelBase):
    creator_id: uuid.UUID

class ChannelResponse(ChannelBase):
    id: uuid.UUID
    creator_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VideoBase(BaseModel):
    youtube_video_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    sync_status: str = "pending"

class VideoResponse(VideoBase):
    id: uuid.UUID
    channel_id: uuid.UUID
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
