import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class Insight(Base, TimestampMixin):
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)

    topic = Column(String, nullable=False)
    label = Column(String, nullable=False)
    percentage = Column(Float, nullable=False)
    comment_count = Column(Integer, default=0)
    
    sample_comments = Column(JSONB, nullable=True)

    analysis = relationship("Analysis", back_populates="insights")
