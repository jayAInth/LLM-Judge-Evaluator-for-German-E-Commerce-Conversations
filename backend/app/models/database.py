"""
Database Models and Connection Management

SQLAlchemy async models for the LLM Judge framework.
"""

import uuid
from datetime import datetime
from typing import Optional, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class JobStatus(str, PyEnum):
    """Status of batch evaluation jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversationCategory(str, PyEnum):
    """Categories of customer support conversations."""
    RETOURE = "retoure"
    BESCHWERDE = "beschwerde"
    PRODUKTANFRAGE = "produktanfrage"
    LIEFERUNG = "lieferung"
    ZAHLUNG = "zahlung"
    KONTO = "konto"
    ALLGEMEIN = "allgemein"


class Conversation(Base):
    """
    Stored conversation for evaluation.

    Represents a single customer support conversation with metadata
    and optional PII redaction flags.
    """
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(
        Enum(ConversationCategory), default=ConversationCategory.ALLGEMEIN
    )
    messages: Mapped[list] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Timestamps
    conversation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # GDPR fields
    pii_redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_category_created", "category", "created_at"),
        Index("ix_conversations_retention", "retention_expires_at"),
    )


class Evaluation(Base):
    """
    Evaluation result from the LLM judge.

    Stores the complete evaluation including dimension scores,
    chain-of-thought reasoning, and flags.
    """
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_jobs.id", ondelete="SET NULL")
    )

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Analysis
    chain_of_thought: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    improvement_suggestions: Mapped[list] = mapped_column(JSONB, default=list)

    # Flags
    critical_error: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_issue: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_needed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    raw_response: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="evaluations")
    job: Mapped[Optional["EvaluationJob"]] = relationship(back_populates="evaluations")
    human_annotations: Mapped[list["HumanAnnotation"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_evaluations_overall_score", "overall_score"),
        Index("ix_evaluations_flags", "critical_error", "compliance_issue", "escalation_needed"),
        Index("ix_evaluations_evaluated_at", "evaluated_at"),
    )


class EvaluationJob(Base):
    """
    Batch evaluation job tracking.

    Represents a batch processing job with progress tracking
    and error handling.
    """
    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, index=True
    )

    # Configuration
    rubric_name: Mapped[str] = mapped_column(String(100), default="default_rubric")
    batch_size: Mapped[int] = mapped_column(Integer, default=100)
    include_few_shot: Mapped[bool] = mapped_column(Boolean, default=True)

    # Progress
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    completed_conversations: Mapped[int] = mapped_column(Integer, default=0)
    failed_conversations: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # User tracking
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="job")


class HumanAnnotation(Base):
    """
    Human annotation for meta-evaluation.

    Stores human expert scores for calibrating and validating
    the LLM judge's performance.
    """
    __tablename__ = "human_annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE")
    )
    annotator_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Feedback
    agreement_with_judge: Mapped[Optional[bool]] = mapped_column(Boolean)
    disagreement_reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    annotated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    evaluation: Mapped["Evaluation"] = relationship(back_populates="human_annotations")

    __table_args__ = (
        UniqueConstraint("evaluation_id", "annotator_id", name="uq_annotation_per_annotator"),
        Index("ix_human_annotations_annotator", "annotator_id"),
    )


class AuditLog(Base):
    """
    GDPR-compliant audit logging.

    Tracks all significant actions for compliance and debugging.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )


class Rubric(Base):
    """
    Custom rubric configurations.

    Allows storing and versioning custom rubrics beyond the default.
    """
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_rubric_name_version"),
    )


# Database engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
