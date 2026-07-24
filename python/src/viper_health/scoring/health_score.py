"""
Health scoring engine for viper-health.

Aggregates detector findings into a 0-100 health score with severity bands.

Spec reference: Section 6 (Health Score Contract)

Severity bands:
- 85-100: Good
- 70-84: Watch
- 50-69: Degraded
- <50: Critical

Component weights (initial model):
- tiny_file_pressure: 20
- directory_density: 10
- metadata_pressure: 20
- mft_health: 15
- storage_latency_trend: 10
- indexer_health: 10
- cache_churn: 15
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Severity band thresholds
GOOD_THRESHOLD = 85
WATCH_THRESHOLD = 70
DEGRADED_THRESHOLD = 50

# Component weights (must sum to 100)
DEFAULT_WEIGHTS = {
    "tiny_file_pressure": 20.0,
    "directory_density": 10.0,
    "metadata_pressure": 20.0,
    "mft_health": 15.0,
    "storage_latency_trend": 10.0,
    "indexer_health": 10.0,
    "cache_churn": 15.0,
}

SeverityBand = Literal["good", "watch", "degraded", "critical"]


@dataclass(frozen=True)
class ComponentScore:
    """Score for a single detector component (0-100)."""

    name: str
    score: float  # 0.0 to 100.0
    weight: float  # Contribution weight
    weighted_contribution: float  # score * weight / 100


@dataclass(frozen=True)
class HealthScore:
    """Aggregated health score with component breakdown."""

    overall_score: float  # 0.0 to 100.0
    severity_band: SeverityBand
    components: tuple[ComponentScore, ...]


def classify_severity(score: float) -> SeverityBand:
    """
    Classify a numeric score into a severity band.

    Args:
        score: Numeric score (0-100)

    Returns:
        Severity band: "good", "watch", "degraded", or "critical"
    """
    if score >= GOOD_THRESHOLD:
        return "good"
    elif score >= WATCH_THRESHOLD:
        return "watch"
    elif score >= DEGRADED_THRESHOLD:
        return "degraded"
    else:
        return "critical"


def calculate_component_score(
    finding_count: int,
    warning_threshold: int,
    critical_threshold: int,
) -> float:
    """
    Calculate a 0-100 score for a detector component.

    Score logic:
    - 0 findings → 100 (perfect)
    - At warning threshold → 70
    - At critical threshold → 30
    - Beyond critical → approaches 0

    Args:
        finding_count: Number of findings detected
        warning_threshold: Count threshold for warning severity
        critical_threshold: Count threshold for critical severity

    Returns:
        Score from 0.0 to 100.0
    """
    if finding_count == 0:
        return 100.0

    if finding_count <= warning_threshold:
        # Linear decay from 100 to 70 between 0 and warning
        ratio = finding_count / warning_threshold
        return 100.0 - (30.0 * ratio)

    if finding_count <= critical_threshold:
        # Linear decay from 70 to 30 between warning and critical
        ratio = (finding_count - warning_threshold) / (critical_threshold - warning_threshold)
        return 70.0 - (40.0 * ratio)

    # Beyond critical: asymptotic decay toward 0
    excess = finding_count - critical_threshold
    excess_ratio = excess / critical_threshold
    # Decay formula: 30 * (1 / (1 + excess_ratio))
    return 30.0 / (1.0 + excess_ratio)


def calculate_health_score(
    component_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> HealthScore:
    """
    Calculate aggregate health score from component scores.

    Args:
        component_scores: Dictionary mapping component name to raw score (0-100)
        weights: Optional custom weights (defaults to DEFAULT_WEIGHTS)

    Returns:
        HealthScore with overall score, severity band, and component breakdown
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Calculate weighted contributions
    components_list: list[ComponentScore] = []
    total_weighted_score = 0.0

    for name, raw_score in component_scores.items():
        weight = weights.get(name, 0.0)
        weighted_contribution = (raw_score * weight) / 100.0

        components_list.append(
            ComponentScore(
                name=name,
                score=raw_score,
                weight=weight,
                weighted_contribution=weighted_contribution,
            )
        )

        total_weighted_score += weighted_contribution

    # Normalize by total weight used
    total_weight = sum(weights.get(name, 0.0) for name in component_scores)
    overall_score = (total_weighted_score / total_weight) * 100.0 if total_weight > 0 else 0.0

    # Classify severity
    severity = classify_severity(overall_score)

    return HealthScore(
        overall_score=overall_score,
        severity_band=severity,
        components=tuple(components_list),
    )
