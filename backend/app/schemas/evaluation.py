"""
Pydantic Schemas for API Request/Response Validation

These schemas define the contract for the API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict


# Enums
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversationCategory(str, Enum):
    RETOURE = "retoure"
    BESCHWERDE = "beschwerde"
    PRODUKTANFRAGE = "produktanfrage"
    LIEFERUNG = "lieferung"
    ZAHLUNG = "zahlung"
    KONTO = "konto"
    ALLGEMEIN = "allgemein"


# Message schemas
class MessageCreate(BaseModel):
    """Single message in a conversation."""
    role: str = Field(..., description="Role: 'customer', 'chatbot', or 'agent'")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: Optional[datetime] = None


# Conversation schemas
class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    external_id: Optional[str] = Field(None, max_length=255)
    category: ConversationCategory = ConversationCategory.ALLGEMEIN
    messages: list[MessageCreate] = Field(..., min_length=1)
    conversation_timestamp: datetime
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)

    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        if len(v) < 2:
            raise ValueError('Conversation must have at least 2 messages')
        return v


class ConversationResponse(BaseModel):
    """Schema for conversation responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: Optional[str]
    category: str
    messages: list[dict]
    metadata_json: Optional[dict]
    conversation_timestamp: datetime
    created_at: datetime
    pii_redacted: bool


class ConversationBatchCreate(BaseModel):
    """Schema for batch conversation upload."""
    conversations: list[ConversationCreate] = Field(..., max_length=1000)


# Dimension score schemas
class DimensionScoreResponse(BaseModel):
    """Single dimension score in evaluation."""
    score: float = Field(..., ge=0, le=10)
    weight: float = Field(..., ge=0, le=1)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)


class ChainOfThoughtResponse(BaseModel):
    """Chain-of-thought analysis."""
    context_analysis: str
    response_analysis: str
    legal_check: str
    language_assessment: str


class EvaluationFlagsResponse(BaseModel):
    """Evaluation flags."""
    critical_error: bool = False
    compliance_issue: bool = False
    escalation_needed: bool = False


# Evaluation schemas
class EvaluationResponse(BaseModel):
    """Complete evaluation response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    overall_score: float
    dimension_scores: dict[str, DimensionScoreResponse]
    chain_of_thought: ChainOfThoughtResponse
    summary: str
    improvement_suggestions: list[str]
    critical_error: bool
    compliance_issue: bool
    escalation_needed: bool
    model_name: str
    rubric_version: str
    processing_time_ms: int
    evaluated_at: datetime


class EvaluationListResponse(BaseModel):
    """Paginated list of evaluations."""
    items: list[EvaluationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class EvaluationSingleRequest(BaseModel):
    """Request for evaluating a single conversation."""
    conversation_id: uuid.UUID
    rubric_name: str = "default_rubric"
    include_few_shot: bool = True
    include_calibration: bool = True


class EvaluationInlineRequest(BaseModel):
    """Request for evaluating a conversation inline (without storing)."""
    conversation: ConversationCreate
    rubric_name: str = "default_rubric"
    include_few_shot: bool = True


# Job schemas
class JobCreate(BaseModel):
    """Schema for creating a batch evaluation job."""
    name: Optional[str] = None
    conversation_ids: Optional[list[uuid.UUID]] = None
    category_filter: Optional[ConversationCategory] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    rubric_name: str = "default_rubric"
    batch_size: int = Field(default=100, ge=1, le=1000)
    include_few_shot: bool = True


class JobResponse(BaseModel):
    """Schema for job responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: Optional[str]
    status: JobStatus
    rubric_name: str
    batch_size: int
    total_conversations: int
    completed_conversations: int
    failed_conversations: int
    progress_percent: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobProgressResponse(BaseModel):
    """Real-time job progress."""
    job_id: uuid.UUID
    status: JobStatus
    progress_percent: float
    completed: int
    total: int
    failed: int
    estimated_seconds_remaining: Optional[int]


# Human annotation schemas
class HumanAnnotationCreate(BaseModel):
    """Schema for creating human annotations."""
    evaluation_id: uuid.UUID
    annotator_id: str = Field(..., min_length=1, max_length=100)
    overall_score: float = Field(..., ge=0, le=10)
    dimension_scores: dict[str, float]
    agreement_with_judge: Optional[bool] = None
    disagreement_reason: Optional[str] = None
    notes: Optional[str] = None


class HumanAnnotationResponse(BaseModel):
    """Schema for human annotation responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_id: uuid.UUID
    annotator_id: str
    overall_score: float
    dimension_scores: dict
    agreement_with_judge: Optional[bool]
    disagreement_reason: Optional[str]
    annotated_at: datetime


# Statistics schemas
class DimensionStats(BaseModel):
    """Statistics for a single dimension."""
    dimension: str
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    count: int


class CategoryStats(BaseModel):
    """Statistics for a category."""
    category: str
    count: int
    mean_score: float
    flag_rate: float


class OverallStats(BaseModel):
    """Overall evaluation statistics."""
    total_evaluations: int
    total_conversations: int
    mean_overall_score: float
    median_overall_score: float
    critical_error_rate: float
    compliance_issue_rate: float
    escalation_rate: float
    dimension_stats: list[DimensionStats]
    category_stats: list[CategoryStats]
    score_distribution: dict[str, int]  # Score ranges to counts


class TimeSeriesPoint(BaseModel):
    """Single point in time series data."""
    timestamp: datetime
    value: float
    count: int


class TimeSeriesResponse(BaseModel):
    """Time series data for dashboards."""
    metric: str
    granularity: str  # hour, day, week
    data: list[TimeSeriesPoint]


# Meta-evaluation schemas
class CorrelationMetrics(BaseModel):
    """Correlation metrics between judge and human annotations."""
    pearson_r: float
    spearman_rho: float
    kendall_tau: float
    mean_absolute_error: float
    root_mean_squared_error: float
    cohen_kappa: float
    sample_size: int


class MetaEvaluationResponse(BaseModel):
    """Meta-evaluation results."""
    overall_correlation: CorrelationMetrics
    dimension_correlations: dict[str, CorrelationMetrics]
    calibration_needed: bool
    recommendations: list[str]
    last_calculated: datetime


# Rubric schemas
class RubricDimensionConfig(BaseModel):
    """Configuration for a rubric dimension."""
    key: str
    name: str
    weight: float = Field(..., ge=0, le=1)
    description: str
    criteria: str
    critical_threshold: int = Field(default=3, ge=0, le=10)


class RubricCreate(BaseModel):
    """Schema for creating custom rubrics."""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    description: Optional[str] = None
    dimensions: list[RubricDimensionConfig]

    @field_validator('dimensions')
    @classmethod
    def validate_weights(cls, v):
        total_weight = sum(d.weight for d in v)
        if not 0.99 <= total_weight <= 1.01:
            raise ValueError(f'Dimension weights must sum to 1.0, got {total_weight}')
        return v


class RubricResponse(BaseModel):
    """Schema for rubric responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    description: Optional[str]
    config: dict
    is_active: bool
    created_at: datetime


# Health check
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    redis: str
    judge_model: str
    timestamp: datetime
