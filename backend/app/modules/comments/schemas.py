import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CommentBase(BaseModel):
    youtube_comment_id: str
    author_name: str
    author_profile_image: str | None = None
    text: str
    like_count: int = 0
    published_at: datetime
    parent_id: uuid.UUID | None = None
    sentiment_score: float | None = None

class CommentCreate(CommentBase):
    video_id: uuid.UUID

class CommentResponse(CommentBase):
    id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class CommentPaginationResponse(BaseModel):
    data: list[CommentResponse]
    pagination: PaginationInfo

