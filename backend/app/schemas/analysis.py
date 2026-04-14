from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class AnalysisBase(BaseModel):
    status: str = "pending"
    total_comments: int = 0

class AnalysisCreate(AnalysisBase):
    video_id: UUID

class AnalysisRead(AnalysisBase):
    id: UUID
    video_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
