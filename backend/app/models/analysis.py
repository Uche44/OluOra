import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    total_comments = Column(Integer, default=0)
    
    completed_at = Column(DateTime, nullable=True)

    video = relationship("Video", back_populates="analyses")
    insights = relationship("Insight", back_populates="analysis", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="analysis", cascade="all, delete-orphan")
