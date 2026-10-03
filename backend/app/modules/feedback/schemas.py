import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeedbackCategory = Literal["bug", "idea", "praise", "other"]
FeedbackStatus = Literal["new", "resolved"]


class FeedbackCreate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    category: FeedbackCategory = "other"
    message: str = Field(min_length=1, max_length=2000)
    page: str | None = Field(default=None, max_length=100)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rating: int | None
    category: str
    message: str
    page: str | None
    status: str
    created_at: datetime
