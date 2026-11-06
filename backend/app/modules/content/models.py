import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContentOpportunity(Base):
    """An evidence-backed content idea generated from one analysis run.

    Opportunities are mutable (saved/dismissed) while the underlying analysis
    artifacts stay immutable. Source FKs use SET NULL so an opportunity survives
    deletion of its video/analysis; the evidence rows keep a short snapshot.
    """

    __tablename__ = "content_opportunities"
    __table_args__ = (
        Index("ix_content_opportunities_creator_status", "creator_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    # Denormalized only so the card still has context if the video is deleted.
    source_video_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_format: Mapped[str] = mapped_column(String(50), default="tutorial", nullable=False)
    suggested_length: Mapped[str] = mapped_column(String(50), default="long_form", nullable=False)
    suggested_angle: Mapped[str] = mapped_column(Text, default="", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    # new | saved | dismissed
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    is_evidence_backed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Identifies the exact analysis inputs used, so repeated clicks reuse the
    # persisted result instead of paying for another LLM call.
    generation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    evidence: Mapped[list["ContentOpportunityEvidence"]] = relationship(
        "ContentOpportunityEvidence",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )


class ContentOpportunityEvidence(Base):
    """A stable reference to the audience evidence behind an opportunity.

    ``quote`` is a short snapshot of the source text. It keeps the evidence
    readable after a source comment/cluster/insight is deleted; we deliberately
    do not duplicate full payloads.
    """

    __tablename__ = "content_opportunity_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insights.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topic_clusters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    opportunity: Mapped["ContentOpportunity"] = relationship(
        "ContentOpportunity", back_populates="evidence"
    )


class ContentCalendarItem(Base):
    """A planned piece of content on a creator's weekly calendar.

    Dates are stored date-only (plus an optional local wall-clock time) for the
    MVP. Opportunities are optional: creators can add manual items too. If the
    source opportunity is deleted, the item survives with its copied fields.
    """

    __tablename__ = "content_calendar_items"
    __table_args__ = (
        Index("ix_content_calendar_items_creator_date", "creator_id", "scheduled_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    angle: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Optional pasted transcript/outline used when captions are unavailable.
    content_context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="tutorial", nullable=False)
    # long_form | short
    length: Mapped[str] = mapped_column(String(50), default="long_form", nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    # idea | planned | in_progress | ready | published
    status: Mapped[str] = mapped_column(String(20), default="idea", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class ContentScript(Base):
    """A generated script/brief version for a calendar item.

    Versions are immutable snapshots unless the creator edits them. Regenerating
    creates a new version, so creator edits are never silently overwritten.
    """

    __tablename__ = "content_scripts"
    __table_args__ = (
        UniqueConstraint(
            "calendar_item_id", "version", name="uq_content_scripts_item_version"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_calendar_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    working_title: Mapped[str] = mapped_column(String(255), nullable=False)
    hook: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Kept as a plain-text fallback/export of ``sections`` for older clients.
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Ordered [{heading, content}] blocks that make the draft editable by section.
    sections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    talking_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    examples: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    cta: Mapped[str] = mapped_column(Text, default="", nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    alt_titles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    user_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class CreatorStyleProfile(Base):
    """Manual style preferences used when generating scripts.

    One row per creator. This is deliberately manual: no inferred style is
    stored here until transcript/reference-content ingestion is approved.
    """

    __tablename__ = "creator_style_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_creator_style_profiles_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    tone: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    language: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    audience_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # beginner | intermediate | advanced
    technical_depth: Mapped[str] = mapped_column(String(50), default="intermediate", nullable=False)
    preferred_structures: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    avoid: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    posting_cadence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    preferred_formats: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preferred_platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reference_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

