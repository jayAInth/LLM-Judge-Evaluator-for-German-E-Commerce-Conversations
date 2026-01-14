"""
Test Judge Components

Quick test script to verify all judge package components work correctly
without requiring database or external services.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_models():
    """Test judge models import and instantiation."""
    print("\n== Testing judge/models.py ==")
    
    from judge.models import (
        JudgeConfig, JudgeModelProvider, Conversation,
        EvaluationResult, DimensionScore, ChainOfThought,
        EvaluationFlags, Rubric, RubricDimension
    )
    
    # Test JudgeConfig
    config = JudgeConfig(
        provider=JudgeModelProvider.OPENAI_COMPATIBLE,
        model_name="test-model",
        base_url="http://localhost:8080/v1"
    )
    print(f"  ✓ JudgeConfig: {config.model_name}")
    
    # Test Conversation
    conv = Conversation(
        id="test-conv-1",
        category="produktanfrage",
        timestamp=datetime.now(),
        messages=[
            {"role": "customer", "content": "Hallo, ich habe eine Frage."},
            {"role": "chatbot", "content": "Guten Tag! Wie kann ich Ihnen helfen?"}
        ]
    )
    print(f"  ✓ Conversation: {conv.id} with {len(conv.messages)} messages")
    
    # Test DimensionScore
    dim_score = DimensionScore(
        score=4.0,
        weight=0.25,
        reasoning="Good response",
        evidence=["Evidence 1"]
    )
    print(f"  ✓ DimensionScore: {dim_score.score}/5")
    
    # Test RubricDimension
    rubric_dim = RubricDimension(
        name="accuracy",
        weight=0.25,
        description="Factual correctness",
        scoring_guidelines={1: "Very poor", 5: "Excellent"}
    )
    print(f"  ✓ RubricDimension: {rubric_dim.name} ({rubric_dim.weight*100:.0f}%)")
    
    # Test Rubric
    rubric = Rubric(
        name="test_rubric",
        version="1.0.0",
        description="Test rubric",
        dimensions={"accuracy": rubric_dim}
    )
    print(f"  ✓ Rubric: {rubric.name} v{rubric.version}")
    
    print("  ✓ All models OK!")
    return True


def test_rubric_loader():
    """Test rubric loader functionality."""
    print("\n== Testing judge/rubrics/rubric_loader.py ==")
    
    from judge.rubrics.rubric_loader import RubricLoader
    
    loader = RubricLoader()
    print(f"  ✓ RubricLoader initialized with path: {loader.rubrics_dir}")
    
    # Load default rubric
    rubric = loader.load("default_rubric")
    print(f"  ✓ Loaded rubric: {rubric.name} v{rubric.version}")
    print(f"    Dimensions: {list(rubric.dimensions.keys())}")
    
    # List available rubrics
    available = loader.list_available()
    print(f"  ✓ Available rubrics: {available}")
    
    print("  ✓ Rubric loader OK!")
    return True


def test_engine():
    """Test judge engine initialization (without actual LLM calls)."""
    print("\n== Testing judge/engine.py ==")
    
    from judge.engine import JudgeEngine
    from judge.models import JudgeConfig, JudgeModelProvider
    from judge.rubrics.rubric_loader import RubricLoader
    
    config = JudgeConfig(
        provider=JudgeModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-oss-120b",
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
    
    loader = RubricLoader()
    rubric = loader.load("default_rubric")
    
    # Just verify engine initialization
    engine = JudgeEngine(config, rubric)
    print(f"  ✓ JudgeEngine initialized with model: {config.model_name}")
    print(f"    Rubric: {rubric.name}")
    
    # Test prompt building
    system_prompt = engine._build_system_prompt()
    print(f"  ✓ System prompt generated ({len(system_prompt)} chars)")
    
    print("  ✓ Engine OK!")
    return True


async def test_languagetool_integration():
    """Test LanguageTool integration class."""
    print("\n== Testing judge/languagetool.py ==")
    
    from judge.languagetool import LanguageToolIntegration
    from judge.models import EvaluationResult, DimensionScore, ChainOfThought, EvaluationFlags
    
    lt = LanguageToolIntegration()
    print(f"  ✓ LanguageToolIntegration initialized with URL: {lt.base_url}")
    
    # Create a mock result for testing
    mock_result = EvaluationResult(
        conversation_id="test-123",
        overall_score=0.8,
        dimension_scores={
            "language_quality": DimensionScore(
                score=4.0,
                weight=0.10,
                reasoning="Good German language quality",
                evidence=["No major issues"]
            )
        },
        chain_of_thought=ChainOfThought(
            context_analysis="Test context",
            response_analysis="Test response",
            legal_check="No issues",
            language_assessment="Good German"
        ),
        summary="Test summary",
        improvement_suggestions=[],
        flags=EvaluationFlags(),
        model_name="test-model",
        rubric_version="1.0.0",
        processing_time_ms=100
    )
    
    print(f"  ✓ Mock EvaluationResult created: score={mock_result.overall_score:.2f}")
    
    # Test the get_suggestions method (will fail without LanguageTool running, but tests the code path)
    try:
        async with lt:
            suggestions = await lt.get_suggestions("Dies ist ein Test.")
            print(f"  ✓ LanguageTool check completed: {len(suggestions)} suggestions")
    except Exception as e:
        print(f"  ⚠ LanguageTool not running (expected): {type(e).__name__}")
    
    print("  ✓ LanguageTool integration OK!")
    return True


def test_evaluation_service():
    """Test evaluation service imports."""
    print("\n== Testing backend/app/services/evaluation_service.py ==")
    
    from backend.app.services.evaluation_service import EvaluationService
    
    # Initialize without database
    service = EvaluationService(db=None)
    print(f"  ✓ EvaluationService initialized")
    print(f"    Model: {service._judge_config.model_name}")
    print(f"    Provider: {service._judge_config.provider.value}")
    
    print("  ✓ Evaluation service OK!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("LLM-as-Judge Component Tests")
    print("=" * 60)
    
    all_passed = True
    
    try:
        all_passed &= test_models()
    except Exception as e:
        print(f"  ✗ Models test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_rubric_loader()
    except Exception as e:
        print(f"  ✗ Rubric loader test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_engine()
    except Exception as e:
        print(f"  ✗ Engine test failed: {e}")
        all_passed = False
    
    try:
        asyncio.run(test_languagetool_integration())
    except Exception as e:
        print(f"  ✗ LanguageTool integration test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_evaluation_service()
    except Exception as e:
        print(f"  ✗ Evaluation service test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All component tests PASSED!")
    else:
        print("✗ Some tests FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
