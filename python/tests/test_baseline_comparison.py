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
    metric_names = {change.metric_name for change in comparison.changes}
    assert "sequential_write_throughput" in metric_names
    assert "sequential_write_iops" in metric_names


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


def test_compare_to_baseline_mft_fragment_thresholds(tmp_path):
    """Fragment changes only degrade after crossing health thresholds."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"mft_fragments": 1}))

    stable = compare_to_baseline({"mft_fragments": 2}, baseline_path)
    stable_change = next(c for c in stable.changes if c.metric_name == "mft_fragments")
    assert stable_change.severity == "stable"

    degraded = compare_to_baseline({"mft_fragments": 6}, baseline_path)
    degraded_change = next(c for c in degraded.changes if c.metric_name == "mft_fragments")
    assert degraded_change.severity == "degraded"
    assert any("MFT fragmentation" in alert for alert in degraded.alerts)


def test_compare_to_baseline_skips_incompatible_benchmark_blocks(tmp_path):
    """Benchmark values with different block sizes are not compared."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({
        "benchmark_results": [{
            "test_name": "random_read",
            "block_size": 4096,
            "throughput_mb_s": 100,
            "iops": 25_600,
        }],
    }))
    current = {
        "benchmark_results": [{
            "test_name": "random_read",
            "block_size": 8192,
            "throughput_mb_s": 100,
            "iops": 12_800,
        }],
    }

    comparison = compare_to_baseline(current, baseline_path)

    assert comparison.changes == []
    assert comparison.overall_severity == "stable"


def test_compare_to_baseline_skips_unavailable_benchmarks(tmp_path):
    """Graceful-degradation objects are not treated as result lists."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({
        "benchmark_results": {"available": False, "error": "unavailable"},
    }))

    comparison = compare_to_baseline(
        {"benchmark_results": {"available": False, "error": "unavailable"}},
        baseline_path,
    )

    assert comparison.changes == []
    assert comparison.overall_severity == "stable"


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


def test_compare_cross_machine_tiny_file_pressure(tmp_path):
    """Cross-machine: current machine has far more tiny files (degraded)."""
    baseline_path = tmp_path / "desktop.json"
    baseline_data = {
        "timestamp": "2026-01-01",
        "tiny_files": 10_000,
        "tiny_file_ratio": 5.0,
        "free_percent": 40.0,
    }
    baseline_path.write_text(json.dumps(baseline_data))

    # Laptop has 60% more tiny files and less free space.
    current_data = {
        "timestamp": "2026-01-02",
        "tiny_files": 16_000,  # +60% (critical)
        "tiny_file_ratio": 8.0,  # +60% (critical)
        "free_percent": 40.0,
    }

    comparison = compare_to_baseline(current_data, baseline_path)

    metric_names = {c.metric_name for c in comparison.changes}
    assert "tiny_files" in metric_names
    assert "tiny_file_ratio" in metric_names
    assert comparison.overall_severity == "critical"
    assert any("Tiny-file count" in a for a in comparison.alerts)


def test_compare_cross_machine_free_space_drop(tmp_path):
    """Cross-machine: current machine has much less free space (degraded)."""
    baseline_path = tmp_path / "desktop.json"
    baseline_data = {
        "timestamp": "2026-01-01",
        "tiny_files": 10_000,
        "free_percent": 40.0,
    }
    baseline_path.write_text(json.dumps(baseline_data))

    current_data = {
        "timestamp": "2026-01-02",
        "tiny_files": 10_000,  # stable
        "free_percent": 30.0,  # -25% (degraded; higher is better)
    }

    comparison = compare_to_baseline(current_data, baseline_path)

    free_change = next(c for c in comparison.changes if c.metric_name == "free_percent")
    assert free_change.severity == "degraded"
    assert any("Free space decreased" in a for a in comparison.alerts)


def test_compare_cross_machine_stable_when_similar(tmp_path):
    """Cross-machine: near-identical machines report stable with no alerts."""
    baseline_path = tmp_path / "desktop.json"
    baseline_data = {
        "timestamp": "2026-01-01",
        "tiny_files": 10_000,
        "tiny_file_ratio": 5.0,
        "free_percent": 40.0,
        "health_score": {"overall_score": 100.0},
    }
    baseline_path.write_text(json.dumps(baseline_data))

    current_data = {
        "timestamp": "2026-01-02",
        "tiny_files": 10_100,  # +1%
        "tiny_file_ratio": 5.05,
        "free_percent": 39.5,
        "health_score": {"overall_score": 99.0},
    }

    comparison = compare_to_baseline(current_data, baseline_path)

    assert comparison.overall_severity == "stable"
    assert comparison.alerts == []


def test_compare_cross_machine_ignores_non_numeric_metrics(tmp_path):
    """Non-numeric metric values are skipped gracefully."""
    baseline_path = tmp_path / "desktop.json"
    baseline_data = {
        "timestamp": "2026-01-01",
        "free_percent": "unavailable",
        "tiny_files": 10_000,
    }
    baseline_path.write_text(json.dumps(baseline_data))

    current_data = {
        "timestamp": "2026-01-02",
        "free_percent": 30.0,
        "tiny_files": 10_000,
    }

    comparison = compare_to_baseline(current_data, baseline_path)

    metric_names = {c.metric_name for c in comparison.changes}
    assert "free_percent" not in metric_names  # skipped (non-numeric baseline)
    assert "tiny_files" in metric_names
