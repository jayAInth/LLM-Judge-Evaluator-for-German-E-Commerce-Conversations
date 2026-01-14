"""
Evaluation Service

Business logic for running LLM judge evaluations.
"""

import logging
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.database import Conversation, Evaluation
from judge.engine import JudgeEngine
from judge.models import (
    JudgeConfig, JudgeModelProvider, Conversation as JudgeConversation
)
from judge.languagetool import LanguageToolIntegration
from judge.rubrics.rubric_loader import RubricLoader


logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Service for running evaluations on conversations.

    Handles the orchestration of the judge engine, database operations,
    and optional LanguageTool integration.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize the evaluation service.

        Args:
            db: Optional database session for storing results
        """
        self.db = db
        self.rubric_loader = RubricLoader()
        self._judge_config = self._create_judge_config()

    def _create_judge_config(self) -> JudgeConfig:
        """Create judge configuration from settings."""

        logger.info(f"Creating judge config with URL: {settings.JUDGE_API_URL}")
        provider_map = {
            "openai_compatible": JudgeModelProvider.OPENAI_COMPATIBLE,
            "vllm": JudgeModelProvider.VLLM,
            "ollama": JudgeModelProvider.OLLAMA,
            "anthropic": JudgeModelProvider.ANTHROPIC,
        }

        return JudgeConfig(
            provider=provider_map.get(
                settings.JUDGE_MODEL_PROVIDER,
                JudgeModelProvider.OPENAI_COMPATIBLE
            ),
            model_name=settings.JUDGE_MODEL_NAME,
            base_url=settings.JUDGE_API_URL,
            api_key=settings.JUDGE_API_KEY,
            temperature=settings.JUDGE_TEMPERATURE,
            max_tokens=settings.JUDGE_MAX_TOKENS,
            timeout=settings.JUDGE_TIMEOUT,
        )

    async def evaluate_conversation(
        self,
        conversation: Conversation,
        rubric_name: str = "default_rubric",
        include_few_shot: bool = True,
        include_calibration: bool = True,
        job_id: Optional[str] = None,
        enhance_with_languagetool: bool = True
    ) -> Evaluation:
        """
        Evaluate a single conversation and store the result.

        Args:
            conversation: Database conversation model
            rubric_name: Name of the rubric to use
            include_few_shot: Include few-shot examples
            include_calibration: Include calibration guidelines
            job_id: Optional job ID if part of batch
            enhance_with_languagetool: Run additional LanguageTool checks

        Returns:
            Stored Evaluation model
        """
        # Load rubric
        rubric = self.rubric_loader.load(rubric_name)

        # Convert to judge conversation format
        judge_conv = JudgeConversation(
            id=str(conversation.id),
            category=conversation.category,
            timestamp=conversation.conversation_timestamp,
            messages=conversation.messages,
            metadata=conversation.metadata_json or {}
        )

        # Run evaluation
        async with JudgeEngine(self._judge_config, rubric) as engine:
            result = await engine.evaluate(
                judge_conv,
                include_few_shot=include_few_shot,
                include_calibration=include_calibration
            )

            # Optional LanguageTool enhancement
            if enhance_with_languagetool and settings.LANGUAGETOOL_ENABLED:
                try:
                    lt = LanguageToolIntegration(settings.LANGUAGETOOL_URL)
                    chatbot_text = self._extract_chatbot_text(conversation.messages)
                    result = await lt.enhance_evaluation(result, chatbot_text)
                except Exception as e:
                    logger.warning(f"LanguageTool enhancement failed: {e}")

        # Store result if we have a database session
        if self.db:
            evaluation = Evaluation(
                conversation_id=conversation.id,
                job_id=job_id,
                overall_score=result.overall_score,
                dimension_scores={
                    k: {
                        "score": v.score,
                        "weight": v.weight,
                        "reasoning": v.reasoning,
                        "evidence": v.evidence
                    }
                    for k, v in result.dimension_scores.items()
                },
                chain_of_thought={
                    "context_analysis": result.chain_of_thought.context_analysis,
                    "response_analysis": result.chain_of_thought.response_analysis,
                    "legal_check": result.chain_of_thought.legal_check,
                    "language_assessment": result.chain_of_thought.language_assessment
                },
                summary=result.summary,
                improvement_suggestions=result.improvement_suggestions,
                critical_error=result.flags.critical_error,
                compliance_issue=result.flags.compliance_issue,
                escalation_needed=result.flags.escalation_needed,
                model_name=result.model_name,
                rubric_version=result.rubric_version,
                processing_time_ms=result.processing_time_ms,
                raw_response=result.raw_response
            )
            self.db.add(evaluation)
            await self.db.flush()
            await self.db.refresh(evaluation)
            return evaluation

        # Return result without storing
        return self._result_to_dict(result)

    async def evaluate_inline(
        self,
        messages: list[dict],
        category: str,
        rubric_name: str = "default_rubric",
        include_few_shot: bool = True
    ) -> dict:
        """
        Evaluate a conversation inline without database storage.

        Args:
            messages: List of message dicts
            category: Conversation category
            rubric_name: Rubric to use
            include_few_shot: Include few-shot examples

        Returns:
            Evaluation result dict
        """
        rubric = self.rubric_loader.load(rubric_name)

        judge_conv = JudgeConversation(
            id="inline",
            category=category,
            timestamp=datetime.utcnow(),
            messages=messages
        )

        async with JudgeEngine(self._judge_config, rubric) as engine:
            result = await engine.evaluate(
                judge_conv,
                include_few_shot=include_few_shot,
                include_calibration=True
            )

        return self._result_to_dict(result)

    async def evaluate_batch(
        self,
        conversations: list[Conversation],
        rubric_name: str = "default_rubric",
        include_few_shot: bool = True,
        progress_callback: Optional[callable] = None
    ) -> list[Evaluation]:
        """
        Evaluate multiple conversations.

        Args:
            conversations: List of conversations to evaluate
            rubric_name: Rubric to use
            include_few_shot: Include few-shot (only first)
            progress_callback: Optional progress callback(current, total)

        Returns:
            List of Evaluation models
        """
        rubric = self.rubric_loader.load(rubric_name)
        evaluations = []

        # Convert to judge format
        judge_convs = [
            JudgeConversation(
                id=str(c.id),
                category=c.category,
                timestamp=c.conversation_timestamp,
                messages=c.messages,
                metadata=c.metadata_json or {}
            )
            for c in conversations
        ]

        async with JudgeEngine(self._judge_config, rubric) as engine:
            results = await engine.evaluate_batch(
                judge_convs,
                include_few_shot=include_few_shot,
                include_calibration=True,
                progress_callback=progress_callback
            )

        # Store results
        if self.db:
            for conv, result in zip(conversations, results):
                evaluation = Evaluation(
                    conversation_id=conv.id,
                    overall_score=result.overall_score,
                    dimension_scores={
                        k: {
                            "score": v.score,
                            "weight": v.weight,
                            "reasoning": v.reasoning,
                            "evidence": v.evidence
                        }
                        for k, v in result.dimension_scores.items()
                    },
                    chain_of_thought={
                        "context_analysis": result.chain_of_thought.context_analysis,
                        "response_analysis": result.chain_of_thought.response_analysis,
                        "legal_check": result.chain_of_thought.legal_check,
                        "language_assessment": result.chain_of_thought.language_assessment
                    },
                    summary=result.summary,
                    improvement_suggestions=result.improvement_suggestions,
                    critical_error=result.flags.critical_error,
                    compliance_issue=result.flags.compliance_issue,
                    escalation_needed=result.flags.escalation_needed,
                    model_name=result.model_name,
                    rubric_version=result.rubric_version,
                    processing_time_ms=result.processing_time_ms
                )
                self.db.add(evaluation)
                evaluations.append(evaluation)

            await self.db.flush()

        return evaluations

    def _extract_chatbot_text(self, messages: list[dict]) -> str:
        """Extract chatbot responses from messages for language checking."""
        chatbot_texts = []
        for msg in messages:
            role = msg.get("role", "").lower()
            if role in ("chatbot", "assistant", "agent"):
                chatbot_texts.append(msg.get("content", ""))
        return "\n\n".join(chatbot_texts)

    def _result_to_dict(self, result) -> dict:
        """Convert evaluation result to dict."""
        return {
            "conversation_id": result.conversation_id,
            "overall_score": result.overall_score,
            "dimension_scores": {
                k: {
                    "score": v.score,
                    "weight": v.weight,
                    "reasoning": v.reasoning,
                    "evidence": v.evidence
                }
                for k, v in result.dimension_scores.items()
            },
            "chain_of_thought": {
                "context_analysis": result.chain_of_thought.context_analysis,
                "response_analysis": result.chain_of_thought.response_analysis,
                "legal_check": result.chain_of_thought.legal_check,
                "language_assessment": result.chain_of_thought.language_assessment
            },
            "summary": result.summary,
            "improvement_suggestions": result.improvement_suggestions,
            "flags": {
                "critical_error": result.flags.critical_error,
                "compliance_issue": result.flags.compliance_issue,
                "escalation_needed": result.flags.escalation_needed
            },
            "model_name": result.model_name,
            "rubric_version": result.rubric_version,
            "processing_time_ms": result.processing_time_ms
        }
