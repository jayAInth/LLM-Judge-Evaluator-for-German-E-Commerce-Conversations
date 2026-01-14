"""
Rubric Loader

Loads and manages evaluation rubrics from configuration files.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from judge.models import Rubric, RubricDimension

logger = logging.getLogger(__name__)

# Default rubric configuration
DEFAULT_RUBRIC = Rubric(
    name="default_rubric",
    version="1.0.0",
    description="Standard evaluation rubric for German e-commerce customer support",
    dimensions={
        "accuracy": RubricDimension(
            name="Accuracy",
            weight=0.25,
            description="Factual correctness of product/policy information",
            scoring_guidelines={
                1: "Multiple factual errors, incorrect product/policy information",
                2: "Some factual errors or incomplete information",
                3: "Mostly accurate with minor issues",
                4: "Accurate information with good detail",
                5: "Completely accurate, comprehensive, and precise"
            }
        ),
        "tone": RubricDimension(
            name="Tone",
            weight=0.20,
            description="Professional, helpful, empathetic communication style",
            scoring_guidelines={
                1: "Rude, dismissive, or inappropriate tone",
                2: "Cold or impersonal, lacks empathy",
                3: "Neutral and professional but not warm",
                4: "Friendly, helpful, and empathetic",
                5: "Excellent rapport, perfectly balanced professionalism and warmth"
            }
        ),
        "compliance": RubricDimension(
            name="Compliance",
            weight=0.20,
            description="Adherence to legal requirements (Widerrufsrecht, DSGVO, etc.)",
            scoring_guidelines={
                1: "Violates legal requirements or provides illegal advice",
                2: "Missing required legal information",
                3: "Basic compliance but could be more thorough",
                4: "Good compliance with relevant regulations",
                5: "Excellent compliance, proactively addresses legal aspects"
            }
        ),
        "completeness": RubricDimension(
            name="Completeness",
            weight=0.15,
            description="Full resolution of customer inquiry",
            scoring_guidelines={
                1: "Does not address the customer's question",
                2: "Partially addresses the inquiry, missing key points",
                3: "Addresses main question but misses some details",
                4: "Thoroughly addresses the inquiry",
                5: "Comprehensive response anticipating follow-up questions"
            }
        ),
        "language_quality": RubricDimension(
            name="Language Quality",
            weight=0.10,
            description="German grammar, spelling, and natural phrasing",
            scoring_guidelines={
                1: "Many grammar/spelling errors, unnatural phrasing",
                2: "Noticeable errors affecting readability",
                3: "Minor errors, generally readable",
                4: "Good German with rare minor issues",
                5: "Flawless German, natural and professional"
            }
        ),
        "efficiency": RubricDimension(
            name="Efficiency",
            weight=0.10,
            description="Concise responses without unnecessary verbosity",
            scoring_guidelines={
                1: "Extremely verbose or too brief to be useful",
                2: "Unnecessarily long or missing important details",
                3: "Adequate length but could be more concise",
                4: "Well-balanced, appropriately detailed",
                5: "Perfectly concise, every word serves a purpose"
            }
        )
    },
    few_shot_examples=[
        {
            "conversation": [
                {"role": "customer", "content": "Ich möchte meine Bestellung stornieren."},
                {"role": "chatbot", "content": "Gerne helfe ich Ihnen bei der Stornierung. Könnten Sie mir bitte Ihre Bestellnummer mitteilen? Sie finden diese in Ihrer Bestellbestätigung. Bitte beachten Sie, dass eine kostenlose Stornierung innerhalb von 14 Tagen nach Bestellung gemäß Ihrem Widerrufsrecht möglich ist."}
            ],
            "evaluation": {
                "overall_score": 0.85,
                "summary": "Helpful response that correctly addresses the cancellation request and mentions legal rights."
            }
        }
    ],
    calibration_notes="""
## Calibration Guidelines
- Score 3 should be the baseline for acceptable performance
- Reserve 5 for truly exceptional responses
- Consider context: complex inquiries may have lower completeness expectations
- German language quality is important but shouldn't dominate the score
- Compliance issues should be flagged even for minor violations
"""
)


class RubricLoader:
    """
    Loads evaluation rubrics from files or returns defaults.
    """

    def __init__(self, rubrics_dir: Optional[Path] = None):
        """
        Initialize the rubric loader.

        Args:
            rubrics_dir: Directory containing rubric JSON files
        """
        if rubrics_dir is None:
            rubrics_dir = Path(__file__).parent / "configs"
        self.rubrics_dir = Path(rubrics_dir)
        self._cache: dict[str, Rubric] = {}

    def load(self, rubric_name: str = "default_rubric") -> Rubric:
        """
        Load a rubric by name.

        Args:
            rubric_name: Name of the rubric to load

        Returns:
            Rubric configuration
        """
        # Return cached rubric if available
        if rubric_name in self._cache:
            return self._cache[rubric_name]

        # Return default rubric
        if rubric_name == "default_rubric":
            self._cache[rubric_name] = DEFAULT_RUBRIC
            return DEFAULT_RUBRIC

        # Try to load from file
        rubric_file = self.rubrics_dir / f"{rubric_name}.json"
        if rubric_file.exists():
            try:
                rubric = self._load_from_file(rubric_file)
                self._cache[rubric_name] = rubric
                return rubric
            except Exception as e:
                logger.error(f"Failed to load rubric {rubric_name}: {e}")

        # Fall back to default
        logger.warning(f"Rubric '{rubric_name}' not found, using default")
        return DEFAULT_RUBRIC

    def _load_from_file(self, path: Path) -> Rubric:
        """Load a rubric from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        dimensions = {}
        for dim_name, dim_data in data.get("dimensions", {}).items():
            dimensions[dim_name] = RubricDimension(
                name=dim_data.get("name", dim_name),
                weight=dim_data.get("weight", 0.1),
                description=dim_data.get("description", ""),
                scoring_guidelines={
                    int(k): v for k, v in dim_data.get("scoring_guidelines", {}).items()
                }
            )

        return Rubric(
            name=data.get("name", path.stem),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            dimensions=dimensions,
            few_shot_examples=data.get("few_shot_examples", []),
            calibration_notes=data.get("calibration_notes", "")
        )

    def list_available(self) -> list[str]:
        """List all available rubric names."""
        rubrics = ["default_rubric"]

        if self.rubrics_dir.exists():
            for path in self.rubrics_dir.glob("*.json"):
                rubrics.append(path.stem)

        return rubrics
