"""
LanguageTool Integration

Integration with LanguageTool for German grammar and spelling checks.
"""

import logging
from typing import Optional

import httpx

from judge.models import EvaluationResult, DimensionScore

logger = logging.getLogger(__name__)


class LanguageToolIntegration:
    """
    Integration with LanguageTool API for grammar checking.

    Enhances LLM evaluations with objective grammar/spelling metrics.
    """

    def __init__(self, base_url: str = "http://localhost:8081/v2"):
        """
        Initialize LanguageTool integration.

        Args:
            base_url: Base URL for LanguageTool API
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_text(self, text: str, language: str = "de-DE") -> dict:
        """
        Check text for grammar and spelling errors.

        Args:
            text: Text to check
            language: Language code (default: German)

        Returns:
            Dict with matches (errors) and metrics
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self._client.post(
                f"{self.base_url}/check",
                data={
                    "text": text,
                    "language": language,
                    "enabledOnly": "false"
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"LanguageTool check failed: {e}")
            return {"matches": [], "error": str(e)}

    async def enhance_evaluation(
        self,
        result: EvaluationResult,
        chatbot_text: str
    ) -> EvaluationResult:
        """
        Enhance an evaluation result with LanguageTool analysis.

        Args:
            result: Original evaluation result
            chatbot_text: Chatbot response text to analyze

        Returns:
            Enhanced evaluation result
        """
        if not chatbot_text.strip():
            return result

        check_result = await self.check_text(chatbot_text)
        matches = check_result.get("matches", [])

        # Calculate error metrics
        word_count = len(chatbot_text.split())
        error_count = len(matches)
        error_rate = error_count / max(word_count, 1)

        # Categorize errors
        grammar_errors = []
        spelling_errors = []
        style_errors = []

        for match in matches:
            rule = match.get("rule", {})
            category = rule.get("category", {}).get("id", "")
            message = match.get("message", "")

            if "SPELLER" in category or "SPELLING" in category:
                spelling_errors.append(message)
            elif "GRAMMAR" in category:
                grammar_errors.append(message)
            else:
                style_errors.append(message)

        # Adjust language_quality score if present
        if "language_quality" in result.dimension_scores:
            original_score = result.dimension_scores["language_quality"].score

            # Calculate adjustment based on error rate
            if error_rate > 0.1:
                adjustment = -2
            elif error_rate > 0.05:
                adjustment = -1
            elif error_rate > 0.02:
                adjustment = -0.5
            else:
                adjustment = 0

            new_score = max(1, min(5, original_score + adjustment))

            # Update the dimension score
            original_dim = result.dimension_scores["language_quality"]
            result.dimension_scores["language_quality"] = DimensionScore(
                score=new_score,
                weight=original_dim.weight,
                reasoning=f"{original_dim.reasoning} [LanguageTool: {error_count} issues found - {len(grammar_errors)} grammar, {len(spelling_errors)} spelling, {len(style_errors)} style]",
                evidence=original_dim.evidence + [f"LanguageTool error rate: {error_rate:.2%}"]
            )

            # Recalculate overall score
            total_weight = sum(ds.weight for ds in result.dimension_scores.values())
            result.overall_score = sum(
                (ds.score / 5.0) * ds.weight
                for ds in result.dimension_scores.values()
            ) / total_weight if total_weight > 0 else result.overall_score

        return result

    async def get_suggestions(self, text: str) -> list[dict]:
        """
        Get improvement suggestions for text.

        Args:
            text: Text to analyze

        Returns:
            List of suggestions with context and replacements
        """
        check_result = await self.check_text(text)
        suggestions = []

        for match in check_result.get("matches", []):
            suggestions.append({
                "message": match.get("message", ""),
                "context": match.get("context", {}).get("text", ""),
                "offset": match.get("offset", 0),
                "length": match.get("length", 0),
                "replacements": [r.get("value", "") for r in match.get("replacements", [])[:3]],
                "rule": match.get("rule", {}).get("id", ""),
                "category": match.get("rule", {}).get("category", {}).get("name", "")
            })

        return suggestions
