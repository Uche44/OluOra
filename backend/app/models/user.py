import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=True)

    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
