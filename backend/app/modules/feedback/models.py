import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Feedback(Base):
    """A single piece of feedback submitted by a creator.

    ``user_id``/``email`` are captured from the authenticated submitter but kept
    nullable so a submission survives account deletion (``ON DELETE SET NULL``).
    """

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Overall satisfaction, 1-5. Optional so a minimal text note still lands.
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Which page the widget was opened from, for context during triage.
    page: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Triage state: "new" | "resolved".
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Feedback {self.id} {self.category} {self.status}>"
