import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class WaitlistEntryCreate(BaseModel):
    email: EmailStr

class WaitlistEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    source: str
    ip_address: str | None
