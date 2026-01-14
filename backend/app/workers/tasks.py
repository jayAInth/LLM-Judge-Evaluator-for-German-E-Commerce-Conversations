"""
Celery Tasks for Batch Processing

Async tasks for batch evaluation, data cleanup, and maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.workers.celery_app import celery_app
from backend.app.core.config import settings
from backend.app.models.database import (
    async_session_factory, Conversation, Evaluation,
    EvaluationJob, AuditLog, JobStatus
)
from backend.app.services.evaluation_service import EvaluationService


logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def run_batch_evaluation(
    self,
    job_id: str,
    conversation_ids: Optional[list[str]] = None,
    category_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Run a batch evaluation job.

    Args:
        job_id: UUID of the evaluation job
        conversation_ids: Optional list of specific conversation IDs
        category_filter: Optional category to filter by
        date_from: Optional start date (ISO format)
        date_to: Optional end date (ISO format)
    """
    return run_async(_run_batch_evaluation_async(
        self, job_id, conversation_ids, category_filter, date_from, date_to
    ))


async def _run_batch_evaluation_async(
    task,
    job_id: str,
    conversation_ids: Optional[list[str]],
    category_filter: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str]
):
    """Async implementation of batch evaluation."""
    async with async_session_factory() as db:
        # Get job
        result = await db.execute(
            select(EvaluationJob).where(EvaluationJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Job {job_id} not found")
            return {"error": "Job not found"}

        try:
            # Update job status
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.utcnow()
            await db.commit()

            # Build query for conversations
            query = select(Conversation)
            conditions = []

            if conversation_ids:
                conditions.append(
                    Conversation.id.in_([uuid.UUID(cid) for cid in conversation_ids])
                )
            if category_filter:
                conditions.append(Conversation.category == category_filter)
            if date_from:
                conditions.append(
                    Conversation.conversation_timestamp >= datetime.fromisoformat(date_from)
                )
            if date_to:
                conditions.append(
                    Conversation.conversation_timestamp <= datetime.fromisoformat(date_to)
                )

            if conditions:
                query = query.where(and_(*conditions))

            # Get conversations in batches
            batch_size = job.batch_size
            offset = 0
            completed = 0
            failed = 0

            service = EvaluationService(db)

            while True:
                # Fetch batch
                batch_query = query.offset(offset).limit(batch_size)
                result = await db.execute(batch_query)
                conversations = result.scalars().all()

                if not conversations:
                    break

                # Evaluate batch
                for conv in conversations:
                    try:
                        await service.evaluate_conversation(
                            conversation=conv,
                            rubric_name=job.rubric_name,
                            include_few_shot=(completed == 0 and job.include_few_shot),
                            job_id=job.id
                        )
                        completed += 1

                    except Exception as e:
                        logger.error(f"Failed to evaluate conversation {conv.id}: {e}")
                        failed += 1

                    # Update progress
                    job.completed_conversations = completed
                    job.failed_conversations = failed
                    job.progress_percent = (completed + failed) / job.total_conversations * 100

                    # Estimate completion time
                    if completed > 0:
                        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                        rate = completed / elapsed
                        remaining = job.total_conversations - (completed + failed)
                        if rate > 0:
                            job.estimated_completion = datetime.utcnow() + timedelta(
                                seconds=remaining / rate
                            )

                    await db.commit()

                    # Update Celery task state
                    task.update_state(
                        state="PROGRESS",
                        meta={
                            "completed": completed,
                            "failed": failed,
                            "total": job.total_conversations,
                            "progress_percent": job.progress_percent
                        }
                    )

                offset += batch_size

            # Mark job complete
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100.0
            await db.commit()

            logger.info(
                f"Job {job_id} completed: {completed} successful, {failed} failed"
            )

            return {
                "status": "completed",
                "completed": completed,
                "failed": failed,
                "total": job.total_conversations
            }

        except SoftTimeLimitExceeded:
            job.status = JobStatus.FAILED.value
            job.error_message = "Task timed out"
            await db.commit()
            raise

        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            await db.commit()

            # Retry if possible
            if task.request.retries < task.max_retries:
                raise task.retry(exc=e, countdown=60 * (task.request.retries + 1))

            return {"error": str(e)}


@celery_app.task(bind=True, max_retries=2)
def run_single_evaluation(
    self,
    conversation_id: str,
    rubric_name: str = "default_rubric"
):
    """
    Run evaluation on a single conversation.

    Args:
        conversation_id: UUID of the conversation
        rubric_name: Name of the rubric to use
    """
    return run_async(_run_single_evaluation_async(
        self, conversation_id, rubric_name
    ))


async def _run_single_evaluation_async(
    task,
    conversation_id: str,
    rubric_name: str
):
    """Async implementation of single evaluation."""
    async with async_session_factory() as db:
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return {"error": "Conversation not found"}

        try:
            service = EvaluationService(db)
            evaluation = await service.evaluate_conversation(
                conversation=conversation,
                rubric_name=rubric_name
            )

            return {
                "status": "completed",
                "evaluation_id": str(evaluation.id),
                "overall_score": evaluation.overall_score
            }

        except Exception as e:
            logger.exception(f"Failed to evaluate {conversation_id}: {e}")
            if task.request.retries < task.max_retries:
                raise task.retry(exc=e, countdown=30)
            return {"error": str(e)}


@celery_app.task
def cleanup_expired_data():
    """
    Clean up expired data according to retention policy.

    GDPR compliance: Remove conversations past retention period.
    """
    return run_async(_cleanup_expired_data_async())


async def _cleanup_expired_data_async():
    """Async implementation of data cleanup."""
    async with async_session_factory() as db:
        now = datetime.utcnow()

        # Find expired conversations
        result = await db.execute(
            select(Conversation).where(
                Conversation.retention_expires_at <= now
            )
        )
        expired = result.scalars().all()

        deleted_count = 0
        for conv in expired:
            # Log deletion for audit
            audit = AuditLog(
                action="auto_delete",
                resource_type="conversation",
                resource_id=str(conv.id),
                details={"reason": "retention_expired"}
            )
            db.add(audit)

            await db.delete(conv)
            deleted_count += 1

        await db.commit()

        logger.info(f"Cleaned up {deleted_count} expired conversations")

        return {"deleted": deleted_count}


@celery_app.task
def cleanup_deletion_requests():
    """
    Process pending deletion requests (GDPR Article 17).
    """
    return run_async(_cleanup_deletion_requests_async())


async def _cleanup_deletion_requests_async():
    """Async implementation of deletion request processing."""
    async with async_session_factory() as db:
        # Find conversations with deletion requests older than 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)

        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.deletion_requested_at.isnot(None),
                    Conversation.deletion_requested_at <= cutoff
                )
            )
        )
        to_delete = result.scalars().all()

        deleted_count = 0
        for conv in to_delete:
            audit = AuditLog(
                action="gdpr_delete",
                resource_type="conversation",
                resource_id=str(conv.id),
                details={"reason": "user_request"}
            )
            db.add(audit)

            await db.delete(conv)
            deleted_count += 1

        await db.commit()

        logger.info(f"Processed {deleted_count} GDPR deletion requests")

        return {"deleted": deleted_count}


@celery_app.task
def update_statistics_cache():
    """
    Update cached statistics for dashboard performance.
    """
    return run_async(_update_statistics_cache_async())


async def _update_statistics_cache_async():
    """Async implementation of statistics cache update."""
    import redis.asyncio as redis
    from sqlalchemy import func

    async with async_session_factory() as db:
        # Calculate various statistics
        stats = {}

        # Total counts
        stats["total_conversations"] = (
            await db.execute(select(func.count()).select_from(Conversation))
        ).scalar()

        stats["total_evaluations"] = (
            await db.execute(select(func.count()).select_from(Evaluation))
        ).scalar()

        # Average scores
        avg_result = await db.execute(
            select(func.avg(Evaluation.overall_score))
        )
        stats["avg_overall_score"] = float(avg_result.scalar() or 0)

        # Flag rates
        if stats["total_evaluations"] > 0:
            critical_count = (await db.execute(
                select(func.count()).select_from(Evaluation).where(
                    Evaluation.critical_error == True
                )
            )).scalar()
            stats["critical_error_rate"] = critical_count / stats["total_evaluations"]

            compliance_count = (await db.execute(
                select(func.count()).select_from(Evaluation).where(
                    Evaluation.compliance_issue == True
                )
            )).scalar()
            stats["compliance_issue_rate"] = compliance_count / stats["total_evaluations"]

        # Store in Redis cache
        try:
            r = redis.from_url(settings.REDIS_URL)
            import json
            await r.set(
                "dashboard_stats",
                json.dumps(stats),
                ex=settings.REDIS_CACHE_TTL
            )
            await r.close()
        except Exception as e:
            logger.warning(f"Failed to update Redis cache: {e}")

        return stats


@celery_app.task
def recalculate_meta_evaluation():
    """
    Recalculate meta-evaluation metrics.
    """
    return run_async(_recalculate_meta_evaluation_async())


async def _recalculate_meta_evaluation_async():
    """Async implementation of meta-evaluation recalculation."""
    from backend.app.services.meta_evaluation_service import MetaEvaluationService

    async with async_session_factory() as db:
        service = MetaEvaluationService(db)
        metrics = await service.calculate_metrics()

        # Store results
        try:
            import redis.asyncio as redis
            import json
            r = redis.from_url(settings.REDIS_URL)
            await r.set(
                "meta_evaluation_metrics",
                json.dumps(metrics.model_dump(), default=str),
                ex=86400  # 24 hours
            )
            await r.close()
        except Exception as e:
            logger.warning(f"Failed to cache meta-evaluation: {e}")

        return metrics.model_dump()
