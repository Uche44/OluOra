import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class Video(Base, TimestampMixin):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    social_account_id = Column(UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True)

    platform = Column(String, nullable=False)
    platform_video_id = Column(String, nullable=False)

    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    published_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="videos")
    social_account = relationship("SocialAccount", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")
