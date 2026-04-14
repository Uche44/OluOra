import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.base import TimestampMixin

class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)

    question_text = Column(String, nullable=False)
    frequency = Column(Integer, default=1)

    analysis = relationship("Analysis", back_populates="questions")
