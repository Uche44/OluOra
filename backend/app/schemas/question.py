from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class QuestionBase(BaseModel):
    question_text: str
    frequency: int = 1

class QuestionCreate(QuestionBase):
    analysis_id: UUID

class QuestionRead(QuestionBase):
    id: UUID
    analysis_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
