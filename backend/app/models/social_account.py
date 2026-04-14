import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class SocialAccount(Base, TimestampMixin):
    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    platform = Column(String, nullable=False)  # 'youtube' | 'tiktok'
    platform_user_id = Column(String, nullable=False)
    username = Column(String, nullable=True)
    
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_expiry = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="social_accounts")
    videos = relationship("Video", back_populates="social_account", cascade="all, delete-orphan")
