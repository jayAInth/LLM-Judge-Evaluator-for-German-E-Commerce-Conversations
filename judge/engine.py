"""
Judge Engine

Core evaluation engine that uses LLMs to evaluate customer support conversations.
"""

import asyncio
import json
import logging
import time
from typing import Optional, Callable, Any

import httpx

from judge.models import (
    JudgeConfig,
    JudgeModelProvider,
    Conversation,
    EvaluationResult,
    DimensionScore,
    ChainOfThought,
    EvaluationFlags,
    Rubric,
)

logger = logging.getLogger(__name__)


class JudgeEngine:
    """
    LLM-as-Judge evaluation engine.

    Uses large language models to evaluate customer support conversations
    against a configurable rubric.
    """

    def __init__(self, config: JudgeConfig, rubric: Rubric):
        """
        Initialize the judge engine.

        Args:
            config: Judge configuration
            rubric: Evaluation rubric
        """
        self.config = config
        self.rubric = rubric
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = httpx.Timeout(
            connect=30.0,
            read=self.config.timeout,
            write=30.0,
            pool=30.0
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the judge."""
        dimensions_text = "\n".join([
            f"- **{dim.name}** ({dim.weight*100:.0f}%): {dim.description}"
            for dim in self.rubric.dimensions.values()
        ])

        return f"""You are an expert evaluator for German e-commerce customer support chatbot conversations.

Your task is to evaluate chatbot responses against the following rubric:

## Evaluation Dimensions
{dimensions_text}

## Instructions
1. Analyze the conversation context and customer intent
2. Evaluate the chatbot's response against each dimension
3. Check for legal/compliance issues (Widerrufsrecht, DSGVO, etc.)
4. Assess German language quality
5. Provide an overall score and actionable feedback

## Output Format
You MUST respond with a valid JSON object in the following format:
{{
    "chain_of_thought": {{
        "context_analysis": "Analysis of customer context and intent",
        "response_analysis": "Analysis of chatbot response quality",
        "legal_check": "Check for legal/compliance issues",
        "language_assessment": "Assessment of German language quality"
    }},
    "dimension_scores": {{
        "accuracy": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}},
        "tone": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}},
        "compliance": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}},
        "completeness": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}},
        "language_quality": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}},
        "efficiency": {{"score": 1-5, "reasoning": "...", "evidence": ["..."]}}
    }},
    "flags": {{
        "critical_error": false,
        "compliance_issue": false,
        "escalation_needed": false
    }},
    "summary": "Brief overall assessment",
    "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}}

{self.rubric.calibration_notes}
"""

    def _build_user_prompt(self, conversation: Conversation, include_few_shot: bool = True) -> str:
        """Build the user prompt with the conversation to evaluate."""
        few_shot_text = ""
        if include_few_shot and self.rubric.few_shot_examples:
            few_shot_text = "\n## Examples\n"
            for i, example in enumerate(self.rubric.few_shot_examples[:2], 1):
                few_shot_text += f"\n### Example {i}\n"
                few_shot_text += f"Conversation: {json.dumps(example.get('conversation', []), ensure_ascii=False)}\n"
                few_shot_text += f"Expected evaluation: {json.dumps(example.get('evaluation', {}), ensure_ascii=False)}\n"

        messages_text = "\n".join([
            f"**{msg.get('role', 'unknown').upper()}**: {msg.get('content', '')}"
            for msg in conversation.messages
        ])

        return f"""{few_shot_text}
## Conversation to Evaluate
**Category**: {conversation.category}
**Conversation ID**: {conversation.id}

{messages_text}

Please evaluate this conversation and respond with the JSON evaluation.
"""

    async def evaluate(
        self,
        conversation: Conversation,
        include_few_shot: bool = True,
        include_calibration: bool = True
    ) -> EvaluationResult:
        """
        Evaluate a single conversation.

        Args:
            conversation: The conversation to evaluate
            include_few_shot: Include few-shot examples in prompt
            include_calibration: Include calibration guidelines

        Returns:
            EvaluationResult with scores and analysis
        """
        start_time = time.time()

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(conversation, include_few_shot)

        try:
            response = await self._call_llm(system_prompt, user_prompt)
            result = self._parse_response(response, conversation.id)
        except Exception as e:
            logger.error(f"Evaluation failed for {conversation.id}: {e}")
            result = self._create_error_result(conversation.id, str(e))

        processing_time = int((time.time() - start_time) * 1000)
        result.processing_time_ms = processing_time
        result.model_name = self.config.model_name
        result.rubric_version = self.rubric.version

        return result

    async def evaluate_batch(
        self,
        conversations: list[Conversation],
        include_few_shot: bool = True,
        include_calibration: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        concurrency: int = 5
    ) -> list[EvaluationResult]:
        """
        Evaluate multiple conversations with concurrency control.

        Args:
            conversations: List of conversations to evaluate
            include_few_shot: Include few-shot examples (only first)
            include_calibration: Include calibration guidelines
            progress_callback: Optional callback(current, total)
            concurrency: Max concurrent evaluations

        Returns:
            List of EvaluationResults
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = []
        completed = 0

        async def evaluate_with_semaphore(conv: Conversation, idx: int) -> EvaluationResult:
            nonlocal completed
            async with semaphore:
                # Only include few-shot for first conversation
                result = await self.evaluate(
                    conv,
                    include_few_shot=(include_few_shot and idx == 0),
                    include_calibration=include_calibration
                )
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(conversations))
                return result

        tasks = [
            evaluate_with_semaphore(conv, idx)
            for idx, conv in enumerate(conversations)
        ]
        results = await asyncio.gather(*tasks)

        return results

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM API."""
        if not self._client:
            raise RuntimeError("JudgeEngine must be used as async context manager")

        if self.config.provider == JudgeModelProvider.ANTHROPIC:
            return await self._call_anthropic(system_prompt, user_prompt)
        else:
            return await self._call_openai_compatible(system_prompt, user_prompt)

    async def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        """Call an OpenAI-compatible API."""
        url = f"{self.config.base_url}/chat/completions"
        logger.info(f"Calling LLM API at: {url} with model: {self.config.model_name}")

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key and self.config.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Anthropic API."""
        url = "https://api.anthropic.com/v1/messages"

        payload = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }

        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]

    def _parse_response(self, response: str, conversation_id: str) -> EvaluationResult:
        """Parse the LLM response into an EvaluationResult."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return self._create_error_result(conversation_id, f"JSON parse error: {e}")

        # Parse dimension scores
        dimension_scores = {}
        for dim_name, dim_data in data.get("dimension_scores", {}).items():
            weight = self.rubric.dimensions.get(dim_name, RubricDimension(dim_name, 0.1, "", {})).weight if dim_name in self.rubric.dimensions else 0.1
            dimension_scores[dim_name] = DimensionScore(
                score=dim_data.get("score", 3),
                weight=weight,
                reasoning=dim_data.get("reasoning", ""),
                evidence=dim_data.get("evidence", [])
            )

        # Calculate overall score (weighted average, normalized to 0-1)
        if dimension_scores:
            total_weight = sum(ds.weight for ds in dimension_scores.values())
            overall_score = sum(
                (ds.score / 5.0) * ds.weight
                for ds in dimension_scores.values()
            ) / total_weight if total_weight > 0 else 0.5
        else:
            overall_score = 0.5

        # Parse chain of thought
        cot_data = data.get("chain_of_thought", {})
        chain_of_thought = ChainOfThought(
            context_analysis=cot_data.get("context_analysis", ""),
            response_analysis=cot_data.get("response_analysis", ""),
            legal_check=cot_data.get("legal_check", ""),
            language_assessment=cot_data.get("language_assessment", "")
        )

        # Parse flags
        flags_data = data.get("flags", {})
        flags = EvaluationFlags(
            critical_error=flags_data.get("critical_error", False),
            compliance_issue=flags_data.get("compliance_issue", False),
            escalation_needed=flags_data.get("escalation_needed", False)
        )

        return EvaluationResult(
            conversation_id=conversation_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            chain_of_thought=chain_of_thought,
            summary=data.get("summary", ""),
            improvement_suggestions=data.get("improvement_suggestions", []),
            flags=flags,
            model_name="",  # Set by caller
            rubric_version="",  # Set by caller
            processing_time_ms=0,  # Set by caller
            raw_response=response
        )

    def _create_error_result(self, conversation_id: str, error: str) -> EvaluationResult:
        """Create an error result when evaluation fails."""
        return EvaluationResult(
            conversation_id=conversation_id,
            overall_score=0.0,
            dimension_scores={},
            chain_of_thought=ChainOfThought(
                context_analysis=f"Error: {error}",
                response_analysis="",
                legal_check="",
                language_assessment=""
            ),
            summary=f"Evaluation failed: {error}",
            improvement_suggestions=[],
            flags=EvaluationFlags(critical_error=True),
            model_name="",
            rubric_version="",
            processing_time_ms=0,
            raw_response=None
        )


# Import for backwards compatibility
from judge.models import RubricDimension
