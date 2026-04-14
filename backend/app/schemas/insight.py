from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any

class InsightBase(BaseModel):
    topic: str
    label: str
    percentage: float
    comment_count: int = 0
    sample_comments: Optional[Any] = None  # Using Any for JSONB field

class InsightCreate(InsightBase):
    analysis_id: UUID

class InsightRead(InsightBase):
    id: UUID
    analysis_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
