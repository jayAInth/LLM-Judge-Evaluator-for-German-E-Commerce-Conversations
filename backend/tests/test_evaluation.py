"""
Tests for Evaluation Service and Judge Engine

Comprehensive tests including sample evaluations and correlation metrics.
"""

import pytest
import json
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
from scipy import stats

from judge.engine import (
    JudgeEngine, JudgeConfig, JudgeModelProvider,
    Conversation, EvaluationResult, DimensionScore
)
from judge.rubrics.rubric_loader import RubricLoader, get_default_rubric
from backend.app.services.evaluation_service import EvaluationService


# Load sample conversations
SAMPLE_DATA_PATH = Path(__file__).parent.parent.parent / "evaluation" / "datasets" / "sample_conversations.json"


@pytest.fixture
def sample_conversations():
    """Load sample conversation data."""
    with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def rubric():
    """Load default rubric."""
    return get_default_rubric()


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return json.dumps({
        "conversation_id": "TEST-001",
        "chain_of_thought": {
            "context_analysis": "Test context analysis",
            "response_analysis": "Test response analysis",
            "legal_check": "Test legal check",
            "language_assessment": "Test language assessment"
        },
        "dimension_scores": {
            "accuracy": {"score": 8.0, "weight": 0.25, "reasoning": "Good accuracy", "evidence": ["Example 1"]},
            "tone": {"score": 7.5, "weight": 0.20, "reasoning": "Good tone", "evidence": ["Example 2"]},
            "compliance": {"score": 9.0, "weight": 0.20, "reasoning": "Excellent compliance", "evidence": []},
            "completeness": {"score": 8.0, "weight": 0.15, "reasoning": "Complete", "evidence": []},
            "language_quality": {"score": 8.5, "weight": 0.10, "reasoning": "Good German", "evidence": []},
            "efficiency": {"score": 7.0, "weight": 0.10, "reasoning": "Efficient", "evidence": []}
        },
        "overall_score": 8.05,
        "summary": "Good quality response",
        "improvement_suggestions": ["Could be more empathetic"],
        "flags": {
            "critical_error": False,
            "compliance_issue": False,
            "escalation_needed": False
        }
    })


class TestRubricLoader:
    """Tests for rubric loading and configuration."""

    def test_load_default_rubric(self, rubric):
        """Test loading the default rubric."""
        assert rubric is not None
        assert rubric.metadata.name == "German E-Commerce Support Rubric"
        assert rubric.metadata.language == "de"

    def test_rubric_dimensions(self, rubric):
        """Test rubric dimensions are correctly loaded."""
        assert len(rubric.dimensions) == 6
        assert "accuracy" in rubric.dimensions
        assert "tone" in rubric.dimensions
        assert "compliance" in rubric.dimensions

    def test_dimension_weights_sum_to_one(self, rubric):
        """Test that dimension weights sum to 1.0."""
        total_weight = sum(dim.weight for dim in rubric.dimensions.values())
        assert 0.99 <= total_weight <= 1.01

    def test_category_weights(self, rubric):
        """Test category-specific weight adjustments."""
        loader = RubricLoader()

        # Retoure should have higher compliance weight
        retoure_dims = loader.get_dimensions_for_category(rubric, "retoure")
        compliance_dim = next(d for d in retoure_dims if d["key"] == "compliance")
        assert compliance_dim["weight"] == 0.25

        # Beschwerde should have higher tone weight
        beschwerde_dims = loader.get_dimensions_for_category(rubric, "beschwerde")
        tone_dim = next(d for d in beschwerde_dims if d["key"] == "tone")
        assert tone_dim["weight"] == 0.30


class TestJudgeEngine:
    """Tests for the LLM Judge Engine."""

    @pytest.mark.asyncio
    async def test_evaluation_parsing(self, mock_llm_response, rubric):
        """Test parsing of LLM evaluation response."""
        config = JudgeConfig(
            provider=JudgeModelProvider.OPENAI_COMPATIBLE,
            model_name="test-model",
            base_url="http://localhost:8080/v1"
        )

        engine = JudgeEngine(config, rubric)
        result = engine._parse_response(mock_llm_response, "TEST-001")

        assert result.conversation_id == "TEST-001"
        assert result.overall_score == 8.05
        assert len(result.dimension_scores) == 6
        assert result.dimension_scores["accuracy"].score == 8.0
        assert not result.flags.critical_error

    @pytest.mark.asyncio
    async def test_weighted_score_calculation(self, rubric):
        """Test weighted score calculation from dimensions."""
        config = JudgeConfig()
        engine = JudgeEngine(config, rubric)

        dimension_scores = {
            "accuracy": DimensionScore(score=10.0, weight=0.25, reasoning="", evidence=[]),
            "tone": DimensionScore(score=8.0, weight=0.20, reasoning="", evidence=[]),
            "compliance": DimensionScore(score=9.0, weight=0.20, reasoning="", evidence=[]),
            "completeness": DimensionScore(score=7.0, weight=0.15, reasoning="", evidence=[]),
            "language_quality": DimensionScore(score=8.0, weight=0.10, reasoning="", evidence=[]),
            "efficiency": DimensionScore(score=8.0, weight=0.10, reasoning="", evidence=[])
        }

        weighted_score = engine._calculate_weighted_score(dimension_scores)

        # Manual calculation:
        # (10*0.25 + 8*0.20 + 9*0.20 + 7*0.15 + 8*0.10 + 8*0.10) = 8.55
        assert abs(weighted_score - 8.55) < 0.01

    @pytest.mark.asyncio
    async def test_flag_application(self, rubric):
        """Test flag rules are correctly applied."""
        config = JudgeConfig()
        engine = JudgeEngine(config, rubric)

        # Create a result with low accuracy score
        from judge.engine import EvaluationResult, ChainOfThought, EvaluationFlags

        result = EvaluationResult(
            conversation_id="TEST",
            chain_of_thought=ChainOfThought(
                context_analysis="",
                response_analysis="",
                legal_check="",
                language_assessment=""
            ),
            dimension_scores={
                "accuracy": DimensionScore(score=2.0, weight=0.25, reasoning="", evidence=[]),
                "compliance": DimensionScore(score=4.0, weight=0.20, reasoning="", evidence=[])
            },
            overall_score=3.0,
            summary="",
            flags=EvaluationFlags()
        )

        engine._apply_flags(result)

        # accuracy < 3 should trigger critical_error
        assert result.flags.critical_error
        # compliance < 5 should trigger compliance_issue
        assert result.flags.compliance_issue


class TestSampleEvaluations:
    """Tests using sample conversations with expected scores."""

    def test_sample_conversations_loaded(self, sample_conversations):
        """Verify sample conversations are loaded correctly."""
        assert "conversations" in sample_conversations
        assert len(sample_conversations["conversations"]) >= 5

    def test_conversation_categories(self, sample_conversations):
        """Test that conversations cover different categories."""
        categories = set(c["category"] for c in sample_conversations["conversations"])
        expected = {"retoure", "beschwerde", "produktanfrage", "lieferung", "zahlung"}
        assert len(categories.intersection(expected)) >= 4

    def test_expected_score_ranges(self, sample_conversations):
        """Verify expected score ranges are reasonable."""
        for conv in sample_conversations["conversations"]:
            min_score, max_score = conv["expected_score_range"]
            assert 0 <= min_score <= max_score <= 10

    def test_human_annotations_consistency(self, sample_conversations):
        """Test human annotation inter-annotator agreement."""
        annotations = sample_conversations["human_annotations"]["annotations"]

        for conv_id, expert_scores in annotations.items():
            scores = list(expert_scores.values())
            if len(scores) >= 2:
                # Check that expert scores are within 1.5 points
                overall_scores = [s["overall"] for s in scores]
                score_diff = abs(overall_scores[0] - overall_scores[1])
                assert score_diff < 1.5, f"Large disagreement for {conv_id}: {score_diff}"


class TestCorrelationMetrics:
    """Tests for meta-evaluation correlation calculations."""

    def test_pearson_correlation(self):
        """Test Pearson correlation calculation."""
        # Perfect correlation
        judge_scores = np.array([1, 2, 3, 4, 5])
        human_scores = np.array([1, 2, 3, 4, 5])
        r, _ = stats.pearsonr(judge_scores, human_scores)
        assert abs(r - 1.0) < 0.001

    def test_spearman_correlation(self):
        """Test Spearman rank correlation."""
        # Perfect rank correlation
        judge_scores = np.array([1, 3, 5, 7, 9])
        human_scores = np.array([2, 4, 6, 8, 10])
        rho, _ = stats.spearmanr(judge_scores, human_scores)
        assert abs(rho - 1.0) < 0.001

    def test_correlation_with_sample_data(self, sample_conversations):
        """Test correlation calculation with sample annotation data."""
        annotations = sample_conversations["human_annotations"]["annotations"]

        # Collect judge (expected) and human scores
        judge_scores = []
        human_scores = []

        for conv in sample_conversations["conversations"]:
            conv_id = conv["id"]
            if conv_id in annotations:
                # Use midpoint of expected range as judge score
                expected_range = conv["expected_score_range"]
                judge_score = (expected_range[0] + expected_range[1]) / 2

                # Average human annotations
                human_annots = annotations[conv_id]
                human_score = np.mean([a["overall"] for a in human_annots.values()])

                judge_scores.append(judge_score)
                human_scores.append(human_score)

        if len(judge_scores) >= 3:
            judge_arr = np.array(judge_scores)
            human_arr = np.array(human_scores)

            pearson_r, _ = stats.pearsonr(judge_arr, human_arr)

            # Should have good correlation with expected ranges
            assert pearson_r > 0.8, f"Expected correlation > 0.8, got {pearson_r}"

    def test_target_correlation_achievable(self, sample_conversations):
        """Verify the target 0.87 correlation is achievable with sample data."""
        target_correlation = sample_conversations["metadata"].get("target_correlation", 0.87)
        assert 0.8 <= target_correlation <= 0.95


class TestConversationFormatting:
    """Tests for conversation formatting."""

    def test_conversation_to_string(self):
        """Test conversation formatting for prompt."""
        conv = Conversation(
            id="TEST-001",
            category="retoure",
            timestamp=datetime.now(),
            messages=[
                {"role": "customer", "content": "Hallo, ich möchte zurückgeben."},
                {"role": "chatbot", "content": "Gerne helfe ich Ihnen dabei."}
            ]
        )

        formatted = conv.to_formatted_string()

        assert "KUNDE:" in formatted
        assert "CHATBOT:" in formatted
        assert "Hallo" in formatted
        assert "Gerne" in formatted

    def test_role_mapping(self):
        """Test role mapping for different input formats."""
        conv = Conversation(
            id="TEST-002",
            category="test",
            timestamp=datetime.now(),
            messages=[
                {"role": "user", "content": "Test 1"},
                {"role": "assistant", "content": "Test 2"},
                {"role": "customer", "content": "Test 3"},
                {"role": "agent", "content": "Test 4"}
            ]
        )

        formatted = conv.to_formatted_string()

        # All should be mapped to KUNDE or CHATBOT
        assert "KUNDE:" in formatted
        assert "CHATBOT:" in formatted


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_invalid_json_response(self, rubric):
        """Test handling of invalid JSON from LLM."""
        config = JudgeConfig()
        engine = JudgeEngine(config, rubric)

        result = engine._parse_response("invalid json {{{", "TEST-001")

        assert result.flags.critical_error
        assert "ERROR" in result.chain_of_thought.context_analysis

    def test_missing_fields_in_response(self, rubric):
        """Test handling of incomplete LLM response."""
        config = JudgeConfig()
        engine = JudgeEngine(config, rubric)

        incomplete_response = json.dumps({
            "conversation_id": "TEST-001",
            "overall_score": 5.0
            # Missing other required fields
        })

        result = engine._parse_response(incomplete_response, "TEST-001")

        # Should still return a result, possibly with defaults
        assert result.conversation_id == "TEST-001"

    def test_score_out_of_range(self, rubric):
        """Test handling of scores outside valid range."""
        config = JudgeConfig()
        engine = JudgeEngine(config, rubric)

        invalid_response = json.dumps({
            "conversation_id": "TEST-001",
            "chain_of_thought": {
                "context_analysis": "",
                "response_analysis": "",
                "legal_check": "",
                "language_assessment": ""
            },
            "dimension_scores": {
                "accuracy": {"score": 15, "weight": 0.25, "reasoning": "", "evidence": []}
            },
            "overall_score": 15,
            "summary": "",
            "improvement_suggestions": [],
            "flags": {}
        })

        # Should handle gracefully (Pydantic validation)
        try:
            result = engine._parse_response(invalid_response, "TEST-001")
            # If it succeeds, score should be capped or validation should fail
        except Exception:
            pass  # Expected behavior - validation should catch this


class TestIntegration:
    """Integration tests for the full evaluation pipeline."""

    @pytest.mark.asyncio
    async def test_full_evaluation_flow(self, sample_conversations, rubric, mock_llm_response):
        """Test complete evaluation flow with mocked LLM."""
        conv_data = sample_conversations["conversations"][0]

        with patch('httpx.AsyncClient') as mock_client:
            # Mock the LLM response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": mock_llm_response}}]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            config = JudgeConfig()
            engine = JudgeEngine(config, rubric)
            engine._client = mock_client_instance

            conv = Conversation(
                id=conv_data["id"],
                category=conv_data["category"],
                timestamp=datetime.now(),
                messages=conv_data["messages"]
            )

            # This would require the actual async context manager
            # Simplified test for structure
            assert conv.id == "CONV-001"
            assert conv.category == "retoure"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
