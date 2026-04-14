from pydantic import BaseModel, ConfigDict, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
