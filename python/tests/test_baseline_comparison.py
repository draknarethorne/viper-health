"""Tests for baseline comparison and trend analysis."""

import json
from pathlib import Path

import pytest

from viper_health.analyzers.baseline_comparison import (
    BaselineComparison,
    MetricChange,
    calculate_change,
    compare_to_baseline,
)


def test_metric_change_dataclass():
    """Test MetricChange dataclass creation."""
    change = MetricChange(
        metric_name="throughput",
        baseline_value=200.0,
        current_value=180.0,
        change_percent=-10.0,
        severity="degraded",
    )
    
    assert change.metric_name == "throughput"
    assert change.baseline_value == 200.0
    assert change.current_value == 180.0
    assert change.change_percent == -10.0
    assert change.severity == "degraded"


def test_calculate_change_degraded_higher_better():
    """Test change calculation for degraded metric (higher is better)."""
    change = calculate_change(
        "throughput",
        200.0,  # baseline
        170.0,  # current (-15%)
        threshold_warning=10,
        threshold_critical=20,
        higher_is_better=True,
    )
    
    assert change.change_percent == -15.0
    assert change.severity == "degraded"


def test_calculate_change_critical_higher_better():
    """Test change calculation for critical metric (higher is better)."""
    change = calculate_change(
        "throughput",
        200.0,  # baseline
        150.0,  # current (-25%)
        threshold_warning=10,
        threshold_critical=20,
        higher_is_better=True,
    )
    
    assert change.change_percent == -25.0
    assert change.severity == "critical"


def test_calculate_change_improved():
    """Test change calculation for improved metric."""
    change = calculate_change(
        "throughput",
        200.0,  # baseline
        230.0,  # current (+15%)
        threshold_warning=10,
        threshold_critical=20,
        higher_is_better=True,
    )
    
    assert change.change_percent == 15.0
    assert change.severity == "improved"


def test_calculate_change_stable():
    """Test change calculation for stable metric."""
    change = calculate_change(
        "throughput",
        200.0,  # baseline
        205.0,  # current (+2.5%)
        threshold_warning=10,
        threshold_critical=20,
        higher_is_better=True,
    )
    
    assert change.change_percent == 2.5
    assert change.severity == "stable"


def test_calculate_change_lower_better():
    """Test change calculation for metric where lower is better."""
    change = calculate_change(
        "mft_size",
        2.0,  # baseline GB
        2.5,  # current GB (+25%)
        threshold_warning=10,
        threshold_critical=20,
        higher_is_better=False,
    )
    
    assert change.change_percent == 25.0
    assert change.severity == "critical"


def test_compare_to_baseline_no_file(tmp_path):
    """Test baseline comparison with missing baseline file."""
    baseline_path = tmp_path / "missing.json"
    current_data = {"timestamp": "2024-01-01"}
    
    with pytest.raises(FileNotFoundError):
        compare_to_baseline(current_data, baseline_path)


def test_compare_to_baseline_benchmark_results(tmp_path):
    """Test baseline comparison with benchmark results."""
    # Create baseline file
    baseline_path = tmp_path / "baseline.json"
    baseline_data = {
        "timestamp": "2024-01-01",
        "benchmark_results": [
            {
                "test_name": "sequential_write",
                "throughput_mb_s": 200.0,
                "iops": 51200.0,
            },
            {
                "test_name": "sequential_read",
                "throughput_mb_s": 1000.0,
                "iops": 256000.0,
            },
        ],
    }
    
    with open(baseline_path, "w") as f:
        json.dump(baseline_data, f)
    
    # Current data shows degradation
    current_data = {
        "timestamp": "2024-02-01",
        "benchmark_results": [
            {
                "test_name": "sequential_write",
                "throughput_mb_s": 150.0,  # -25% (critical)
                "iops": 38400.0,
            },
            {
                "test_name": "sequential_read",
                "throughput_mb_s": 950.0,  # -5% (stable)
                "iops": 243200.0,
            },
        ],
    }
    
    comparison = compare_to_baseline(current_data, baseline_path)
    
    assert comparison.baseline_date == "2024-01-01"
    assert comparison.current_date == "2024-02-01"
    assert comparison.overall_severity == "critical"
    assert len(comparison.alerts) > 0
    assert any("sequential_write" in alert for alert in comparison.alerts)


def test_compare_to_baseline_mft_growth(tmp_path):
    """Test baseline comparison with MFT size growth."""
    baseline_path = tmp_path / "baseline.json"
    baseline_data = {
        "timestamp": "2024-01-01",
        "mft_size_bytes": 2_000_000_000,  # 2 GB
    }
    
    with open(baseline_path, "w") as f:
        json.dump(baseline_data, f)
    
    # Current shows 30% growth (critical)
    current_data = {
        "timestamp": "2024-02-01",
        "mft_size_bytes": 2_600_000_000,  # 2.6 GB
    }
    
    comparison = compare_to_baseline(current_data, baseline_path)
    
    assert comparison.overall_severity == "critical"
    assert any("MFT size" in alert for alert in comparison.alerts)


def test_compare_to_baseline_health_score_drop(tmp_path):
    """Test baseline comparison with health score drop."""
    baseline_path = tmp_path / "baseline.json"
    baseline_data = {
        "timestamp": "2024-01-01",
        "health_score": {
            "overall_score": 100.0,
        },
    }
    
    with open(baseline_path, "w") as f:
        json.dump(baseline_data, f)
    
    # Current shows 15% drop (degraded)
    current_data = {
        "timestamp": "2024-02-01",
        "health_score": {
            "overall_score": 85.0,
        },
    }
    
    comparison = compare_to_baseline(current_data, baseline_path)
    
    assert comparison.overall_severity == "degraded"
    assert any("health score" in alert for alert in comparison.alerts)


def test_compare_to_baseline_improvement(tmp_path):
    """Test baseline comparison showing improvement."""
    baseline_path = tmp_path / "baseline.json"
    baseline_data = {
        "timestamp": "2024-01-01",
        "benchmark_results": [
            {
                "test_name": "sequential_write",
                "throughput_mb_s": 150.0,
                "iops": 38400.0,
            },
        ],
    }
    
    with open(baseline_path, "w") as f:
        json.dump(baseline_data, f)
    
    # Current shows improvement
    current_data = {
        "timestamp": "2024-02-01",
        "benchmark_results": [
            {
                "test_name": "sequential_write",
                "throughput_mb_s": 200.0,  # +33% (improved)
                "iops": 51200.0,
            },
        ],
    }
    
    comparison = compare_to_baseline(current_data, baseline_path)
    
    assert comparison.overall_severity == "improved"
    assert len(comparison.alerts) == 0  # No alerts for improvements
