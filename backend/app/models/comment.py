import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    platform_comment_id = Column(String, nullable=True)
    author_name = Column(String, nullable=True)
    text = Column(String, nullable=False)

    like_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)

    video = relationship("Video", back_populates="comments")
