import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        # Backs "does this video have a completed analysis?" (list filter and
        # dashboard count) and the per-video latest-analysis lookup.
        Index("ix_analyses_video_id_status", "video_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False) # pending, running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    comments_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="analyses")
    topic_clusters: Mapped[list["TopicCluster"]] = relationship("TopicCluster", back_populates="analysis", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship("Insight", back_populates="analysis", cascade="all, delete-orphan")

class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="topic_clusters")
    # Historical membership lives in CommentClusterMembership; the legacy
    # `comments.topic_cluster_id` column was removed after backfilling.
    memberships: Mapped[list["CommentClusterMembership"]] = relationship(
        "CommentClusterMembership",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )

class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. feature_request, critical_issue, content_idea
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="insights")


class CommentClusterMembership(Base):
    """The cluster a comment landed in for one specific analysis run.

    Membership used to be a single mutable FK on ``Comment``, so re-running an
    analysis overwrote it and corrupted the history of earlier runs. Scoping the
    relation by ``analysis_id`` makes each run's output immutable.
    """

    __tablename__ = "comment_cluster_memberships"
    __table_args__ = (
        UniqueConstraint("analysis_id", "comment_id", name="uq_ccm_analysis_comment"),
        Index("ix_ccm_analysis_cluster", "analysis_id", "cluster_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topic_clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Distance to the cluster centroid. Useful for finding the most central
    # comments later without re-running clustering.
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    cluster: Mapped["TopicCluster"] = relationship("TopicCluster", back_populates="memberships")
    comment: Mapped["Comment"] = relationship("Comment", back_populates="cluster_memberships")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)  # queued, running, completed, failed
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    video: Mapped["Video"] = relationship("Video")
    analysis: Mapped["Analysis"] = relationship("Analysis")

