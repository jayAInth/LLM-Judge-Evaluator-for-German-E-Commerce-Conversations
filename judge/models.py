"""
Judge Models

Data models for the LLM-as-Judge evaluation framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class JudgeModelProvider(Enum):
    """Supported LLM providers for the judge."""
    OPENAI_COMPATIBLE = "openai_compatible"
    VLLM = "vllm"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


@dataclass
class JudgeConfig:
    """Configuration for the judge engine."""
    provider: JudgeModelProvider = JudgeModelProvider.OPENAI_COMPATIBLE
    model_name: str = "Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4"
    base_url: str = "http://localhost:8080/v1"
    api_key: str = "not-needed"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: float = 120.0


@dataclass
class Conversation:
    """A customer support conversation to evaluate."""
    id: str
    category: str
    timestamp: datetime
    messages: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""
    score: float
    weight: float
    reasoning: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ChainOfThought:
    """Chain of thought reasoning from the judge."""
    context_analysis: str
    response_analysis: str
    legal_check: str
    language_assessment: str


@dataclass
class EvaluationFlags:
    """Flags for critical issues in the evaluation."""
    critical_error: bool = False
    compliance_issue: bool = False
    escalation_needed: bool = False


@dataclass
class EvaluationResult:
    """Complete evaluation result from the judge."""
    conversation_id: str
    overall_score: float
    dimension_scores: dict[str, DimensionScore]
    chain_of_thought: ChainOfThought
    summary: str
    improvement_suggestions: list[str]
    flags: EvaluationFlags
    model_name: str
    rubric_version: str
    processing_time_ms: int
    raw_response: Optional[str] = None


@dataclass
class RubricDimension:
    """A single dimension in an evaluation rubric."""
    name: str
    weight: float
    description: str
    scoring_guidelines: dict[int, str]  # score -> description


@dataclass
class Rubric:
    """Evaluation rubric configuration."""
    name: str
    version: str
    description: str
    dimensions: dict[str, RubricDimension]
    few_shot_examples: list[dict[str, Any]] = field(default_factory=list)
    calibration_notes: str = ""
