"""
Tests for health scoring engine.
"""

import pytest

from viper_health.scoring.health_score import (
    calculate_component_score,
    calculate_health_score,
    classify_severity,
)


def test_classify_severity_good() -> None:
    """Verify good band classification (85-100)."""
    assert classify_severity(100.0) == "good"
    assert classify_severity(90.0) == "good"
    assert classify_severity(85.0) == "good"


def test_classify_severity_watch() -> None:
    """Verify watch band classification (70-84)."""
    assert classify_severity(84.9) == "watch"
    assert classify_severity(75.0) == "watch"
    assert classify_severity(70.0) == "watch"


def test_classify_severity_degraded() -> None:
    """Verify degraded band classification (50-69)."""
    assert classify_severity(69.9) == "degraded"
    assert classify_severity(60.0) == "degraded"
    assert classify_severity(50.0) == "degraded"


def test_classify_severity_critical() -> None:
    """Verify critical band classification (<50)."""
    assert classify_severity(49.9) == "critical"
    assert classify_severity(25.0) == "critical"
    assert classify_severity(0.0) == "critical"


def test_calculate_component_score_perfect() -> None:
    """Verify perfect score (no findings)."""
    score = calculate_component_score(
        finding_count=0,
        warning_threshold=100,
        critical_threshold=200,
    )
    assert score == 100.0


def test_calculate_component_score_at_warning() -> None:
    """Verify score at warning threshold is 70."""
    score = calculate_component_score(
        finding_count=100,
        warning_threshold=100,
        critical_threshold=200,
    )
    assert score == pytest.approx(70.0, abs=0.1)


def test_calculate_component_score_at_critical() -> None:
    """Verify score at critical threshold is 30."""
    score = calculate_component_score(
        finding_count=200,
        warning_threshold=100,
        critical_threshold=200,
    )
    assert score == pytest.approx(30.0, abs=0.1)


def test_calculate_component_score_beyond_critical() -> None:
    """Verify score decays beyond critical threshold."""
    score = calculate_component_score(
        finding_count=400,
        warning_threshold=100,
        critical_threshold=200,
    )
    # Should be less than 30 but greater than 0
    assert 0.0 < score < 30.0


def test_calculate_health_score_perfect() -> None:
    """Verify perfect health score (all components at 100)."""
    component_scores = {
        "tiny_file_pressure": 100.0,
        "directory_density": 100.0,
    }

    weights = {
        "tiny_file_pressure": 20.0,
        "directory_density": 10.0,
    }

    result = calculate_health_score(component_scores, weights)

    assert result.overall_score == pytest.approx(100.0, abs=0.1)
    assert result.severity_band == "good"
    assert len(result.components) == 2


def test_calculate_health_score_weighted_mix() -> None:
    """Verify weighted aggregation."""
    component_scores = {
        "tiny_file_pressure": 80.0,  # weight 20
        "directory_density": 60.0,   # weight 10
    }

    weights = {
        "tiny_file_pressure": 20.0,
        "directory_density": 10.0,
    }

    result = calculate_health_score(component_scores, weights)

    # Expected: (80*20 + 60*10) / 30 = (1600 + 600) / 30 = 73.33
    expected_score = ((80.0 * 20.0) + (60.0 * 10.0)) / 30.0
    assert result.overall_score == pytest.approx(expected_score, abs=0.1)
    assert result.severity_band == "watch"


def test_calculate_health_score_critical_overall() -> None:
    """Verify overall critical score."""
    component_scores = {
        "tiny_file_pressure": 30.0,
        "directory_density": 40.0,
    }

    weights = {
        "tiny_file_pressure": 20.0,
        "directory_density": 10.0,
    }

    result = calculate_health_score(component_scores, weights)

    # Expected: (30*20 + 40*10) / 30 = (600 + 400) / 30 = 33.33
    expected_score = ((30.0 * 20.0) + (40.0 * 10.0)) / 30.0
    assert result.overall_score == pytest.approx(expected_score, abs=0.1)
    assert result.severity_band == "critical"
