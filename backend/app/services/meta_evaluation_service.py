"""
Meta-Evaluation Service

Calculates correlation metrics between LLM judge and human annotations
to validate and calibrate the judge's performance.
"""

import logging
from datetime import datetime
from typing import Optional
import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score, mean_absolute_error, mean_squared_error
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.database import Evaluation, HumanAnnotation
from backend.app.schemas.evaluation import (
    MetaEvaluationResponse, CorrelationMetrics
)


logger = logging.getLogger(__name__)


class MetaEvaluationService:
    """
    Service for calculating meta-evaluation metrics.

    Compares LLM judge scores with human annotations to assess
    judge reliability and identify calibration needs.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the meta-evaluation service.

        Args:
            db: Database session
        """
        self.db = db

    async def calculate_metrics(self) -> MetaEvaluationResponse:
        """
        Calculate comprehensive meta-evaluation metrics.

        Returns:
            MetaEvaluationResponse with correlation metrics and recommendations
        """
        # Get paired judge-human scores
        pairs = await self._get_score_pairs()

        if len(pairs) < 10:
            return MetaEvaluationResponse(
                overall_correlation=CorrelationMetrics(
                    pearson_r=0.0,
                    spearman_rho=0.0,
                    kendall_tau=0.0,
                    mean_absolute_error=0.0,
                    root_mean_squared_error=0.0,
                    cohen_kappa=0.0,
                    sample_size=len(pairs)
                ),
                dimension_correlations={},
                calibration_needed=True,
                recommendations=["Insufficient data for meta-evaluation. Need at least 10 human annotations."],
                last_calculated=datetime.utcnow()
            )

        # Extract overall scores
        judge_scores = np.array([p["judge_overall"] for p in pairs])
        human_scores = np.array([p["human_overall"] for p in pairs])

        # Calculate overall correlation
        overall_correlation = self._calculate_correlation_metrics(
            judge_scores, human_scores
        )

        # Calculate per-dimension correlations
        dimension_correlations = await self._calculate_dimension_correlations(pairs)

        # Determine if calibration is needed
        calibration_needed = self._check_calibration_needed(
            overall_correlation, dimension_correlations
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_correlation, dimension_correlations, calibration_needed
        )

        return MetaEvaluationResponse(
            overall_correlation=overall_correlation,
            dimension_correlations=dimension_correlations,
            calibration_needed=calibration_needed,
            recommendations=recommendations,
            last_calculated=datetime.utcnow()
        )

    async def _get_score_pairs(self) -> list[dict]:
        """Get paired judge and human scores."""
        # Query evaluations with human annotations
        query = select(
            Evaluation.id,
            Evaluation.overall_score,
            Evaluation.dimension_scores,
            HumanAnnotation.overall_score.label("human_overall"),
            HumanAnnotation.dimension_scores.label("human_dimensions")
        ).join(
            HumanAnnotation, Evaluation.id == HumanAnnotation.evaluation_id
        )

        result = await self.db.execute(query)
        rows = result.all()

        pairs = []
        for row in rows:
            pairs.append({
                "evaluation_id": row.id,
                "judge_overall": row.overall_score,
                "human_overall": row.human_overall,
                "judge_dimensions": row.dimension_scores,
                "human_dimensions": row.human_dimensions
            })

        return pairs

    def _calculate_correlation_metrics(
        self,
        judge_scores: np.ndarray,
        human_scores: np.ndarray
    ) -> CorrelationMetrics:
        """Calculate correlation metrics between two score arrays."""
        n = len(judge_scores)

        if n < 2:
            return CorrelationMetrics(
                pearson_r=0.0,
                spearman_rho=0.0,
                kendall_tau=0.0,
                mean_absolute_error=0.0,
                root_mean_squared_error=0.0,
                cohen_kappa=0.0,
                sample_size=n
            )

        # Pearson correlation
        pearson_r, _ = stats.pearsonr(judge_scores, human_scores)

        # Spearman correlation
        spearman_rho, _ = stats.spearmanr(judge_scores, human_scores)

        # Kendall's tau
        kendall_tau, _ = stats.kendalltau(judge_scores, human_scores)

        # Mean Absolute Error
        mae = mean_absolute_error(human_scores, judge_scores)

        # Root Mean Squared Error
        rmse = np.sqrt(mean_squared_error(human_scores, judge_scores))

        # Cohen's Kappa (discretize scores to bins)
        judge_bins = np.digitize(judge_scores, bins=[3, 5, 7, 9])
        human_bins = np.digitize(human_scores, bins=[3, 5, 7, 9])
        kappa = cohen_kappa_score(human_bins, judge_bins)

        return CorrelationMetrics(
            pearson_r=round(float(pearson_r), 4),
            spearman_rho=round(float(spearman_rho), 4),
            kendall_tau=round(float(kendall_tau), 4),
            mean_absolute_error=round(float(mae), 4),
            root_mean_squared_error=round(float(rmse), 4),
            cohen_kappa=round(float(kappa), 4),
            sample_size=n
        )

    async def _calculate_dimension_correlations(
        self,
        pairs: list[dict]
    ) -> dict[str, CorrelationMetrics]:
        """Calculate correlations for each evaluation dimension."""
        dimension_correlations = {}

        # Collect scores by dimension
        dimension_scores = {}
        for pair in pairs:
            judge_dims = pair.get("judge_dimensions", {})
            human_dims = pair.get("human_dimensions", {})

            for dim_key in judge_dims.keys():
                if dim_key not in dimension_scores:
                    dimension_scores[dim_key] = {"judge": [], "human": []}

                judge_score = judge_dims.get(dim_key, {}).get("score")
                human_score = human_dims.get(dim_key)

                if judge_score is not None and human_score is not None:
                    dimension_scores[dim_key]["judge"].append(judge_score)
                    dimension_scores[dim_key]["human"].append(human_score)

        # Calculate correlations for each dimension
        for dim_key, scores in dimension_scores.items():
            if len(scores["judge"]) >= 5:
                judge_arr = np.array(scores["judge"])
                human_arr = np.array(scores["human"])
                dimension_correlations[dim_key] = self._calculate_correlation_metrics(
                    judge_arr, human_arr
                )

        return dimension_correlations

    def _check_calibration_needed(
        self,
        overall: CorrelationMetrics,
        dimensions: dict[str, CorrelationMetrics]
    ) -> bool:
        """Determine if judge calibration is needed."""
        # Calibration needed if:
        # 1. Overall Pearson correlation < 0.80
        # 2. Any dimension correlation < 0.70
        # 3. MAE > 1.0

        if overall.pearson_r < 0.80:
            return True

        if overall.mean_absolute_error > 1.0:
            return True

        for dim_metrics in dimensions.values():
            if dim_metrics.pearson_r < 0.70:
                return True

        return False

    def _generate_recommendations(
        self,
        overall: CorrelationMetrics,
        dimensions: dict[str, CorrelationMetrics],
        calibration_needed: bool
    ) -> list[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []

        # Sample size recommendations
        if overall.sample_size < 50:
            recommendations.append(
                f"Current sample size ({overall.sample_size}) is small. "
                "Aim for at least 50 human annotations for reliable metrics."
            )

        # Correlation recommendations
        if overall.pearson_r < 0.70:
            recommendations.append(
                f"Overall correlation ({overall.pearson_r:.2f}) is below acceptable threshold (0.70). "
                "Consider reviewing prompt engineering and few-shot examples."
            )
        elif overall.pearson_r < 0.80:
            recommendations.append(
                f"Overall correlation ({overall.pearson_r:.2f}) is moderate. "
                "Minor calibration adjustments recommended."
            )
        elif overall.pearson_r >= 0.87:
            recommendations.append(
                f"Excellent correlation ({overall.pearson_r:.2f}) achieved. "
                "Judge is well-calibrated with human assessments."
            )

        # MAE recommendations
        if overall.mean_absolute_error > 1.5:
            recommendations.append(
                f"High mean absolute error ({overall.mean_absolute_error:.2f}). "
                "Judge scores deviate significantly from human scores on average."
            )

        # Dimension-specific recommendations
        weak_dimensions = []
        for dim_key, metrics in dimensions.items():
            if metrics.pearson_r < 0.70:
                weak_dimensions.append(f"{dim_key} ({metrics.pearson_r:.2f})")

        if weak_dimensions:
            recommendations.append(
                f"Weak correlation in dimensions: {', '.join(weak_dimensions)}. "
                "Review rubric criteria and scoring anchors for these dimensions."
            )

        # Calibration recommendation
        if calibration_needed:
            recommendations.append(
                "CALIBRATION RECOMMENDED: Run recalibration process with additional "
                "human annotations to improve judge accuracy."
            )

        if not recommendations:
            recommendations.append("Judge performance is within acceptable parameters.")

        return recommendations

    async def get_inter_annotator_agreement(self) -> dict:
        """
        Calculate inter-annotator agreement for human annotations.

        Returns:
            Dict with Krippendorff's alpha and other agreement metrics
        """
        # Get annotations grouped by evaluation
        query = select(
            HumanAnnotation.evaluation_id,
            HumanAnnotation.annotator_id,
            HumanAnnotation.overall_score
        ).order_by(HumanAnnotation.evaluation_id)

        result = await self.db.execute(query)
        rows = result.all()

        # Group by evaluation
        evaluation_scores = {}
        for row in rows:
            eval_id = str(row.evaluation_id)
            if eval_id not in evaluation_scores:
                evaluation_scores[eval_id] = {}
            evaluation_scores[eval_id][row.annotator_id] = row.overall_score

        # Filter to evaluations with multiple annotators
        multi_annotated = {
            k: v for k, v in evaluation_scores.items()
            if len(v) >= 2
        }

        if len(multi_annotated) < 5:
            return {
                "krippendorff_alpha": None,
                "sample_size": len(multi_annotated),
                "message": "Insufficient multi-annotated samples for agreement calculation"
            }

        # Calculate pairwise agreement
        agreements = []
        for eval_id, scores in multi_annotated.items():
            score_list = list(scores.values())
            for i in range(len(score_list)):
                for j in range(i + 1, len(score_list)):
                    diff = abs(score_list[i] - score_list[j])
                    agreements.append(1 - diff / 10)  # Normalize to 0-1

        avg_agreement = np.mean(agreements) if agreements else 0

        return {
            "average_pairwise_agreement": round(float(avg_agreement), 4),
            "sample_size": len(multi_annotated),
            "total_annotation_pairs": len(agreements)
        }

    async def get_calibration_set(self, size: int = 50) -> list[dict]:
        """
        Get a calibration set of evaluations for human annotation.

        Selects a diverse sample across score ranges and categories.

        Args:
            size: Number of evaluations to include

        Returns:
            List of evaluations needing human annotation
        """
        # Get evaluations without human annotations
        subquery = select(HumanAnnotation.evaluation_id)
        query = select(Evaluation).where(
            Evaluation.id.notin_(subquery)
        )

        # Add stratified sampling by score range
        result = await self.db.execute(query)
        evaluations = result.scalars().all()

        if not evaluations:
            return []

        # Stratify by score ranges
        score_ranges = {
            "low": [e for e in evaluations if e.overall_score < 4],
            "medium": [e for e in evaluations if 4 <= e.overall_score < 7],
            "high": [e for e in evaluations if e.overall_score >= 7]
        }

        # Sample proportionally from each range
        selected = []
        samples_per_range = size // 3

        for range_name, evals in score_ranges.items():
            sample_size = min(samples_per_range, len(evals))
            if sample_size > 0:
                indices = np.random.choice(len(evals), sample_size, replace=False)
                selected.extend([evals[i] for i in indices])

        return [
            {
                "evaluation_id": str(e.id),
                "conversation_id": str(e.conversation_id),
                "judge_overall_score": e.overall_score,
                "dimension_scores": e.dimension_scores,
                "summary": e.summary
            }
            for e in selected[:size]
        ]
