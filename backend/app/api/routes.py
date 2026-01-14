"""
API Routes for LLM Judge Framework

FastAPI routes for conversation management, evaluation,
batch processing, and analytics.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, and_, or_, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.database import (
    get_db, Conversation, Evaluation, EvaluationJob,
    HumanAnnotation, Rubric, AuditLog, JobStatus
)
from backend.app.schemas.evaluation import (
    ConversationCreate, ConversationResponse, ConversationBatchCreate,
    EvaluationResponse, EvaluationListResponse, EvaluationSingleRequest,
    EvaluationInlineRequest, JobCreate, JobResponse, JobListResponse,
    JobProgressResponse, HumanAnnotationCreate, HumanAnnotationResponse,
    OverallStats, TimeSeriesResponse, MetaEvaluationResponse,
    RubricCreate, RubricResponse, HealthResponse, DimensionStats, CategoryStats
)
from backend.app.services.evaluation_service import EvaluationService
from backend.app.workers.tasks import run_batch_evaluation


router = APIRouter()


# Health check
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health and component status."""
    # Check database
    try:
        await db.execute(select(func.now()))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    # Check judge model connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.JUDGE_API_URL}/models")
            if response.status_code == 200:
                judge_status = "healthy"
            else:
                judge_status = f"degraded: status {response.status_code}"
    except Exception as e:
        judge_status = f"unhealthy: {str(e)}"

    overall_status = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall_status = "unhealthy"
    elif "unhealthy" in judge_status or "degraded" in judge_status:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        judge_model=judge_status,
        timestamp=datetime.utcnow()
    )


# Conversation endpoints
@router.post("/conversations", response_model=ConversationResponse, tags=["Conversations"])
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation for evaluation."""
    conversation = Conversation(
        external_id=data.external_id,
        category=data.category.value,
        messages=[m.model_dump() for m in data.messages],
        metadata_json=data.metadata,
        conversation_timestamp=data.conversation_timestamp,
        retention_expires_at=datetime.utcnow() + timedelta(days=settings.DATA_RETENTION_DAYS)
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


@router.post("/conversations/batch", tags=["Conversations"])
async def create_conversations_batch(
    data: ConversationBatchCreate,
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple conversations in a batch."""
    conversations = []
    for conv_data in data.conversations:
        conversation = Conversation(
            external_id=conv_data.external_id,
            category=conv_data.category.value,
            messages=[m.model_dump() for m in conv_data.messages],
            metadata_json=conv_data.metadata,
            conversation_timestamp=conv_data.conversation_timestamp,
            retention_expires_at=datetime.utcnow() + timedelta(days=settings.DATA_RETENTION_DAYS)
        )
        conversations.append(conversation)
        db.add(conversation)

    await db.flush()
    return {"created": len(conversations), "ids": [str(c.id) for c in conversations]}


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation by ID."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations", tags=["Conversations"])
async def list_conversations(
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List conversations with optional filtering."""
    query = select(Conversation)
    if category:
        query = query.where(Conversation.category == category)

    # Count total
    count_query = select(func.count()).select_from(Conversation)
    if category:
        count_query = count_query.where(Conversation.category == category)
    total = (await db.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Conversation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    conversations = result.scalars().all()

    return {
        "items": conversations,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


@router.delete("/conversations/{conversation_id}", tags=["Conversations"])
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation (GDPR Article 17 - Right to Erasure)."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Log deletion for audit
    audit = AuditLog(
        action="delete",
        resource_type="conversation",
        resource_id=str(conversation_id),
        details={"reason": "user_request"}
    )
    db.add(audit)

    await db.delete(conversation)
    return {"deleted": True, "id": str(conversation_id)}


# Evaluation endpoints
@router.post("/evaluations/single", response_model=EvaluationResponse, tags=["Evaluations"])
async def evaluate_single(
    data: EvaluationSingleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Evaluate a single conversation."""
    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == data.conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Run evaluation
    service = EvaluationService(db)
    evaluation = await service.evaluate_conversation(
        conversation=conversation,
        rubric_name=data.rubric_name,
        include_few_shot=data.include_few_shot,
        include_calibration=data.include_calibration
    )

    return evaluation


@router.post("/evaluations/inline", tags=["Evaluations"])
async def evaluate_inline(data: EvaluationInlineRequest):
    """Evaluate a conversation inline without storing."""
    service = EvaluationService(None)
    result = await service.evaluate_inline(
        messages=[m.model_dump() for m in data.conversation.messages],
        category=data.conversation.category.value,
        rubric_name=data.rubric_name,
        include_few_shot=data.include_few_shot
    )
    return result


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse, tags=["Evaluations"])
async def get_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get an evaluation by ID."""
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@router.delete("/evaluations/{evaluation_id}", tags=["Evaluations"])
async def delete_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an evaluation (GDPR Article 17 - Right to Erasure)."""
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Log deletion for audit
    audit = AuditLog(
        action="delete",
        resource_type="evaluation",
        resource_id=str(evaluation_id),
        details={"conversation_id": str(evaluation.conversation_id)}
    )
    db.add(audit)

    await db.delete(evaluation)
    return {"deleted": True, "id": str(evaluation_id)}


@router.get("/evaluations", response_model=EvaluationListResponse, tags=["Evaluations"])
async def list_evaluations(
    conversation_id: Optional[uuid.UUID] = None,
    job_id: Optional[uuid.UUID] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    has_critical_error: Optional[bool] = None,
    has_compliance_issue: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List evaluations with filtering."""
    query = select(Evaluation)

    # Apply filters
    conditions = []
    if conversation_id:
        conditions.append(Evaluation.conversation_id == conversation_id)
    if job_id:
        conditions.append(Evaluation.job_id == job_id)
    if min_score is not None:
        conditions.append(Evaluation.overall_score >= min_score)
    if max_score is not None:
        conditions.append(Evaluation.overall_score <= max_score)
    if has_critical_error is not None:
        conditions.append(Evaluation.critical_error == has_critical_error)
    if has_compliance_issue is not None:
        conditions.append(Evaluation.compliance_issue == has_compliance_issue)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(Evaluation)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = (await db.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Evaluation.evaluated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    return EvaluationListResponse(
        items=evaluations,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


# Job endpoints
@router.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new batch evaluation job."""
    # Count conversations to evaluate
    query = select(func.count()).select_from(Conversation)
    conditions = []

    if data.conversation_ids:
        conditions.append(Conversation.id.in_(data.conversation_ids))
    if data.category_filter:
        conditions.append(Conversation.category == data.category_filter.value)
    if data.date_from:
        conditions.append(Conversation.conversation_timestamp >= data.date_from)
    if data.date_to:
        conditions.append(Conversation.conversation_timestamp <= data.date_to)

    if conditions:
        query = query.where(and_(*conditions))

    total = (await db.execute(query)).scalar()

    if total == 0:
        raise HTTPException(status_code=400, detail="No conversations match the criteria")

    # Create job
    job = EvaluationJob(
        name=data.name or f"Batch Evaluation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        status=JobStatus.PENDING,
        rubric_name=data.rubric_name,
        batch_size=data.batch_size,
        include_few_shot=data.include_few_shot,
        total_conversations=total
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Queue Celery task
    task = run_batch_evaluation.delay(
        str(job.id),
        [str(cid) for cid in data.conversation_ids] if data.conversation_ids else None,
        data.category_filter.value if data.category_filter else None,
        data.date_from.isoformat() if data.date_from else None,
        data.date_to.isoformat() if data.date_to else None
    )

    # Update job with task ID
    job.celery_task_id = task.id
    await db.flush()

    return job


@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a job by ID."""
    result = await db.execute(
        select(EvaluationJob).where(EvaluationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse, tags=["Jobs"])
async def get_job_progress(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get real-time job progress."""
    result = await db.execute(
        select(EvaluationJob).where(EvaluationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate estimated time remaining
    remaining_seconds = None
    if job.started_at and job.completed_conversations > 0:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        rate = job.completed_conversations / elapsed
        remaining = job.total_conversations - job.completed_conversations
        remaining_seconds = int(remaining / rate) if rate > 0 else None

    return JobProgressResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        progress_percent=job.progress_percent,
        completed=job.completed_conversations,
        total=job.total_conversations,
        failed=job.failed_conversations,
        estimated_seconds_remaining=remaining_seconds
    )


@router.get("/jobs", response_model=JobListResponse, tags=["Jobs"])
async def list_jobs(
    status: Optional[JobStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List batch jobs."""
    query = select(EvaluationJob)
    if status:
        query = query.where(EvaluationJob.status == status.value)

    # Count
    count_query = select(func.count()).select_from(EvaluationJob)
    if status:
        count_query = count_query.where(EvaluationJob.status == status.value)
    total = (await db.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(EvaluationJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=jobs,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse, tags=["Jobs"])
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running job."""
    result = await db.execute(
        select(EvaluationJob).where(EvaluationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    # Revoke Celery task
    if job.celery_task_id:
        from backend.app.workers.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    job.status = JobStatus.CANCELLED.value
    await db.flush()

    return job


# Human annotation endpoints
@router.post("/annotations", response_model=HumanAnnotationResponse, tags=["Annotations"])
async def create_annotation(
    data: HumanAnnotationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a human annotation for meta-evaluation."""
    # Verify evaluation exists
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == data.evaluation_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Evaluation not found")

    annotation = HumanAnnotation(
        evaluation_id=data.evaluation_id,
        annotator_id=data.annotator_id,
        overall_score=data.overall_score,
        dimension_scores=data.dimension_scores,
        agreement_with_judge=data.agreement_with_judge,
        disagreement_reason=data.disagreement_reason,
        notes=data.notes
    )
    db.add(annotation)
    await db.flush()
    await db.refresh(annotation)
    return annotation


@router.get("/annotations", tags=["Annotations"])
async def list_annotations(
    evaluation_id: Optional[uuid.UUID] = None,
    annotator_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List human annotations."""
    query = select(HumanAnnotation)
    if evaluation_id:
        query = query.where(HumanAnnotation.evaluation_id == evaluation_id)
    if annotator_id:
        query = query.where(HumanAnnotation.annotator_id == annotator_id)

    query = query.order_by(HumanAnnotation.annotated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    annotations = result.scalars().all()

    return {"items": annotations, "page": page, "page_size": page_size}


# Statistics endpoints
@router.get("/stats/overview", tags=["Statistics"])
async def get_stats_overview(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get overall evaluation statistics."""
    # Base query conditions
    conditions = []
    if date_from:
        conditions.append(Evaluation.evaluated_at >= date_from)
    if date_to:
        conditions.append(Evaluation.evaluated_at <= date_to)

    # Total counts
    eval_query = select(func.count()).select_from(Evaluation)
    if conditions:
        eval_query = eval_query.where(and_(*conditions))
    total_evaluations = (await db.execute(eval_query)).scalar() or 0

    conv_query = select(func.count()).select_from(Conversation)
    total_conversations = (await db.execute(conv_query)).scalar() or 0

    # Evaluations today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.count()).select_from(Evaluation).where(
        Evaluation.evaluated_at >= today_start
    )
    evaluations_today = (await db.execute(today_query)).scalar() or 0

    # Active jobs count
    active_jobs_query = select(func.count()).select_from(EvaluationJob).where(
        EvaluationJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
    )
    active_jobs = (await db.execute(active_jobs_query)).scalar() or 0

    # Score statistics
    score_query = select(
        func.avg(Evaluation.overall_score),
        func.percentile_cont(0.5).within_group(Evaluation.overall_score)
    ).select_from(Evaluation)
    if conditions:
        score_query = score_query.where(and_(*conditions))
    score_result = (await db.execute(score_query)).first()
    mean_score = float(score_result[0] or 0)
    median_score = float(score_result[1] or 0)

    # Flag counts
    critical_errors_query = select(func.count()).select_from(Evaluation).where(
        Evaluation.critical_error == True
    )
    if conditions:
        critical_errors_query = critical_errors_query.where(and_(*conditions))
    critical_errors_count = (await db.execute(critical_errors_query)).scalar() or 0

    compliance_issues_query = select(func.count()).select_from(Evaluation).where(
        Evaluation.compliance_issue == True
    )
    if conditions:
        compliance_issues_query = compliance_issues_query.where(and_(*conditions))
    compliance_issues_count = (await db.execute(compliance_issues_query)).scalar() or 0

    # Category distribution
    category_query = select(
        Conversation.category,
        func.count(Conversation.id)
    ).select_from(Conversation).group_by(Conversation.category)
    category_result = await db.execute(category_query)
    category_distribution = {row[0]: row[1] for row in category_result.fetchall()}

    # Score distribution (buckets of 1)
    score_distribution = {}
    for i in range(11):
        count_query = select(func.count()).select_from(Evaluation).where(
            and_(
                Evaluation.overall_score >= i,
                Evaluation.overall_score < i + 1,
                *conditions
            )
        )
        score_distribution[f"{i}-{i+1}"] = (await db.execute(count_query)).scalar() or 0

    return {
        "total_evaluations": total_evaluations,
        "total_conversations": total_conversations,
        "evaluations_today": evaluations_today,
        "average_score": round(mean_score, 2),
        "median_score": round(median_score, 2),
        "active_jobs": active_jobs,
        "critical_errors_count": critical_errors_count,
        "compliance_issues_count": compliance_issues_count,
        "category_distribution": category_distribution,
        "score_distribution": score_distribution
    }


@router.get("/stats/timeseries", response_model=TimeSeriesResponse, tags=["Statistics"])
async def get_timeseries(
    metric: str = Query(..., description="Metric: avg_score, count, error_rate"),
    granularity: str = Query("day", description="Granularity: hour, day, week"),
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get time series data for dashboards."""
    from sqlalchemy import text

    # Calculate date range
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=days)

    # Determine truncation based on granularity
    trunc_map = {"hour": "hour", "day": "day", "week": "week"}
    trunc = trunc_map.get(granularity, "day")

    # Build aggregation query based on metric
    if metric == "avg_score":
        query = text(f"""
            SELECT
                date_trunc(:trunc, evaluated_at) as timestamp,
                AVG(overall_score) as value,
                COUNT(*) as count
            FROM evaluations
            WHERE evaluated_at >= :date_from AND evaluated_at <= :date_to
            GROUP BY date_trunc(:trunc, evaluated_at)
            ORDER BY timestamp
        """)
    elif metric == "count":
        query = text(f"""
            SELECT
                date_trunc(:trunc, evaluated_at) as timestamp,
                COUNT(*) as value,
                COUNT(*) as count
            FROM evaluations
            WHERE evaluated_at >= :date_from AND evaluated_at <= :date_to
            GROUP BY date_trunc(:trunc, evaluated_at)
            ORDER BY timestamp
        """)
    elif metric == "error_rate":
        query = text(f"""
            SELECT
                date_trunc(:trunc, evaluated_at) as timestamp,
                AVG(CASE WHEN critical_error THEN 1.0 ELSE 0.0 END) as value,
                COUNT(*) as count
            FROM evaluations
            WHERE evaluated_at >= :date_from AND evaluated_at <= :date_to
            GROUP BY date_trunc(:trunc, evaluated_at)
            ORDER BY timestamp
        """)
    else:
        return TimeSeriesResponse(metric=metric, granularity=granularity, data=[])

    result = await db.execute(query, {"trunc": trunc, "date_from": date_from, "date_to": date_to})
    rows = result.fetchall()

    from backend.app.schemas.evaluation import TimeSeriesPoint
    data = [
        TimeSeriesPoint(
            timestamp=row.timestamp,
            value=round(float(row.value or 0), 2),
            count=row.count
        )
        for row in rows
    ]

    return TimeSeriesResponse(
        metric=metric,
        granularity=granularity,
        data=data
    )


# Meta-evaluation endpoint
@router.get("/meta-evaluation", response_model=MetaEvaluationResponse, tags=["Meta-Evaluation"])
async def get_meta_evaluation(db: AsyncSession = Depends(get_db)):
    """Get meta-evaluation metrics comparing judge to human annotations."""
    from backend.app.services.meta_evaluation_service import MetaEvaluationService

    service = MetaEvaluationService(db)
    return await service.calculate_metrics()


# Rubric endpoints
@router.post("/rubrics", response_model=RubricResponse, tags=["Rubrics"])
async def create_rubric(
    data: RubricCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a custom rubric."""
    rubric = Rubric(
        name=data.name,
        version=data.version,
        description=data.description,
        config={
            "dimensions": [d.model_dump() for d in data.dimensions]
        },
        is_active=True
    )
    db.add(rubric)
    await db.flush()
    await db.refresh(rubric)
    return rubric


@router.get("/rubrics", tags=["Rubrics"])
async def list_rubrics(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List available rubrics."""
    query = select(Rubric)
    if active_only:
        query = query.where(Rubric.is_active == True)
    query = query.order_by(Rubric.name, Rubric.version.desc())
    result = await db.execute(query)
    rubrics = result.scalars().all()
    return {"items": rubrics}


@router.get("/rubrics/{rubric_id}", response_model=RubricResponse, tags=["Rubrics"])
async def get_rubric(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a rubric by ID."""
    result = await db.execute(
        select(Rubric).where(Rubric.id == rubric_id)
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return rubric
