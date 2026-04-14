from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class CommentBase(BaseModel):
    platform_comment_id: Optional[str] = None
    author_name: Optional[str] = None
    text: str
    like_count: int = 0
    published_at: Optional[datetime] = None

class CommentCreate(CommentBase):
    video_id: UUID

class CommentRead(CommentBase):
    id: UUID
    video_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
