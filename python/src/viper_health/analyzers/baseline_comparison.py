"""
Baseline comparison and trend analysis.

Compare current health metrics to saved baselines to detect degradation over time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricChange:
    """Represents a change in a metric from baseline to current."""
    
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    severity: str  # "improved" | "stable" | "degraded" | "critical"


@dataclass(frozen=True)
class BaselineComparison:
    """Results of comparing current metrics to baseline."""
    
    baseline_date: str
    current_date: str
    changes: list[MetricChange]
    overall_severity: str
    alerts: list[str]


def compare_to_baseline(
    current_data: dict,
    baseline_path: Path,
) -> BaselineComparison:
    """
    Compare current metrics to saved baseline.
    
    Args:
        current_data: Current scan/benchmark results
        baseline_path: Path to baseline JSON file
    
    Returns:
        BaselineComparison with detected changes and alerts
    
    Raises:
        FileNotFoundError: If baseline file doesn't exist
        ValueError: If baseline format is incompatible
    """
    # Load baseline
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_path}")
    
    with open(baseline_path) as f:
        baseline_data = json.load(f)
    
    # Extract dates
    baseline_date = baseline_data.get("timestamp", "unknown")
    current_date = current_data.get("timestamp", "unknown")
    
    changes = []
    alerts = []
    
    # Compare benchmark metrics if present
    if "benchmark_results" in baseline_data and "benchmark_results" in current_data:
        baseline_results = baseline_data["benchmark_results"]
        current_results = current_data["benchmark_results"]
        
        # Compare each benchmark test
        for baseline_test in baseline_results:
            test_name = baseline_test["test_name"]
            
            # Find matching current test
            current_test = next(
                (t for t in current_results if t["test_name"] == test_name),
                None
            )
            
            if current_test:
                # Compare throughput
                baseline_throughput = baseline_test["throughput_mb_s"]
                current_throughput = current_test["throughput_mb_s"]
                
                change = calculate_change(
                    f"{test_name}_throughput",
                    baseline_throughput,
                    current_throughput,
                    threshold_warning=10,  # >10% degradation = warning
                    threshold_critical=20,  # >20% degradation = critical
                    higher_is_better=True,
                )
                
                changes.append(change)
                
                # Generate alerts for significant degradation
                if change.severity == "critical":
                    alerts.append(
                        f"{test_name}: {abs(change.change_percent):.1f}% throughput decrease "
                        f"({baseline_throughput:.0f} → {current_throughput:.0f} MB/s)"
                    )
                elif change.severity == "degraded":
                    alerts.append(
                        f"{test_name}: {abs(change.change_percent):.1f}% throughput decrease "
                        f"({baseline_throughput:.0f} → {current_throughput:.0f} MB/s)"
                    )
    
    # Compare MFT metrics if present
    if "mft_size_bytes" in baseline_data and "mft_size_bytes" in current_data:
        baseline_mft = baseline_data["mft_size_bytes"]
        current_mft = current_data["mft_size_bytes"]
        
        change = calculate_change(
            "mft_size",
            baseline_mft / (1024**3),  # Convert to GB
            current_mft / (1024**3),
            threshold_warning=10,  # >10% growth = warning
            threshold_critical=25,  # >25% growth = critical
            higher_is_better=False,
        )
        
        changes.append(change)
        
        if change.severity in ("degraded", "critical"):
            alerts.append(
                f"MFT size increased {abs(change.change_percent):.1f}% "
                f"({change.baseline_value:.2f} → {change.current_value:.2f} GB)"
            )
    
    # Compare health scores if present
    if "health_score" in baseline_data and "health_score" in current_data:
        baseline_health = baseline_data["health_score"]["overall_score"]
        current_health = current_data["health_score"]["overall_score"]
        
        change = calculate_change(
            "health_score",
            baseline_health,
            current_health,
            threshold_warning=10,  # >10 point drop = warning
            threshold_critical=20,  # >20 point drop = critical
            higher_is_better=True,
        )
        
        changes.append(change)
        
        if change.severity in ("degraded", "critical"):
            alerts.append(
                f"Overall health score dropped {abs(change.change_percent):.1f}% "
                f"({baseline_health:.0f} → {current_health:.0f})"
            )
    
    # Determine overall severity
    severities = [c.severity for c in changes]
    if "critical" in severities:
        overall_severity = "critical"
    elif "degraded" in severities:
        overall_severity = "degraded"
    elif "improved" in severities:
        overall_severity = "improved"
    else:
        overall_severity = "stable"
    
    return BaselineComparison(
        baseline_date=baseline_date,
        current_date=current_date,
        changes=changes,
        overall_severity=overall_severity,
        alerts=alerts,
    )


def calculate_change(
    metric_name: str,
    baseline_value: float,
    current_value: float,
    *,
    threshold_warning: float = 10,
    threshold_critical: float = 20,
    higher_is_better: bool = True,
) -> MetricChange:
    """
    Calculate change in a metric and determine severity.
    
    Args:
        metric_name: Name of the metric
        baseline_value: Baseline value
        current_value: Current value
        threshold_warning: Percent change for warning (default: 10%)
        threshold_critical: Percent change for critical (default: 20%)
        higher_is_better: True if higher values are better (e.g., throughput)
    
    Returns:
        MetricChange with severity assessment
    """
    # Calculate percent change
    if baseline_value == 0:
        change_percent = 0.0
    else:
        change_percent = ((current_value - baseline_value) / baseline_value) * 100
    
    # Determine severity
    if higher_is_better:
        # For metrics where higher is better (throughput, health score)
        if change_percent <= -threshold_critical:
            severity = "critical"
        elif change_percent <= -threshold_warning:
            severity = "degraded"
        elif change_percent >= threshold_warning:
            severity = "improved"
        else:
            severity = "stable"
    else:
        # For metrics where lower is better (MFT size, file count)
        if change_percent >= threshold_critical:
            severity = "critical"
        elif change_percent >= threshold_warning:
            severity = "degraded"
        elif change_percent <= -threshold_warning:
            severity = "improved"
        else:
            severity = "stable"
    
    return MetricChange(
        metric_name=metric_name,
        baseline_value=baseline_value,
        current_value=current_value,
        change_percent=round(change_percent, 1),
        severity=severity,
    )
