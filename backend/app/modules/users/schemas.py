import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, HttpUrl

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    profile_picture: str | None = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    full_name: str | None = None
    profile_picture: str | None = None
    is_active: bool | None = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SocialAccountBase(BaseModel):
    provider: str = "google"
    provider_user_id: str

class SocialAccountResponse(SocialAccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    token_expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
