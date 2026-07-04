import uuid
from datetime import datetime
from pydantic import BaseModel

class AnalysisBase(BaseModel):
    status: str = "pending"
    comments_analyzed: int = 0

class AnalysisCreate(AnalysisBase):
    video_id: uuid.UUID

class AnalysisResponse(AnalysisBase):
    id: uuid.UUID
    video_id: uuid.UUID
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TopicClusterBase(BaseModel):
    title: str
    summary: str
    size: int = 0
    sentiment_score: float = 0.0

class TopicClusterResponse(TopicClusterBase):
    id: uuid.UUID
    analysis_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class InsightBase(BaseModel):
    type: str
    title: str
    content: str

class InsightResponse(InsightBase):
    id: uuid.UUID
    analysis_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
