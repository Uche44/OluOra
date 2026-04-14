from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class SocialAccountBase(BaseModel):
    platform: str
    platform_user_id: str
    username: Optional[str] = None
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None

class SocialAccountCreate(SocialAccountBase):
    user_id: UUID

class SocialAccountRead(SocialAccountBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
