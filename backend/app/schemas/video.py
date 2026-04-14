from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class VideoBase(BaseModel):
    platform: str
    platform_video_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    published_at: Optional[datetime] = None

class VideoCreate(VideoBase):
    user_id: UUID
    social_account_id: Optional[UUID] = None

class VideoRead(VideoBase):
    id: UUID
    user_id: UUID
    social_account_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
