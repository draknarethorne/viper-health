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
    if (
        isinstance(baseline_data.get("benchmark_results"), list)
        and isinstance(current_data.get("benchmark_results"), list)
    ):
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

            if not current_test:
                continue

            # Schema v2 records benchmark context. Different block sizes are
            # not directly comparable; schema v1 lacks this field and remains
            # supported using its historical 4 KiB default.
            baseline_block = baseline_test.get("block_size")
            current_block = current_test.get("block_size")
            if baseline_block and current_block and baseline_block != current_block:
                continue

            for key, suffix, label, unit in (
                ("throughput_mb_s", "throughput", "throughput", "MB/s"),
                ("iops", "iops", "IOPS", "IOPS"),
            ):
                try:
                    baseline_value = float(baseline_test[key])
                    current_value = float(current_test[key])
                except (KeyError, TypeError, ValueError):
                    continue

                change = calculate_change(
                    f"{test_name}_{suffix}",
                    baseline_value,
                    current_value,
                    threshold_warning=10,
                    threshold_critical=20,
                    higher_is_better=True,
                )
                changes.append(change)

                if change.severity in ("degraded", "critical"):
                    alerts.append(
                        f"{test_name}: {abs(change.change_percent):.1f}% {label} decrease "
                        f"({baseline_value:.0f} → {current_value:.0f} {unit})"
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

    # Fragment count is interpreted against the same absolute health
    # thresholds as the MFT analyzer. A harmless change from one to two
    # fragments must not become a critical percentage-change alert.
    if "mft_fragments" in baseline_data and "mft_fragments" in current_data:
        try:
            baseline_fragments = float(baseline_data["mft_fragments"])
            current_fragments = float(current_data["mft_fragments"])
        except (TypeError, ValueError):
            pass
        else:
            percent = (
                ((current_fragments - baseline_fragments) / baseline_fragments) * 100
                if baseline_fragments
                else 0.0
            )
            if current_fragments >= 10 and current_fragments > baseline_fragments:
                severity = "critical"
            elif current_fragments >= 5 and current_fragments > baseline_fragments:
                severity = "degraded"
            elif current_fragments < baseline_fragments and baseline_fragments >= 5:
                severity = "improved"
            else:
                severity = "stable"
            changes.append(
                MetricChange(
                    metric_name="mft_fragments",
                    baseline_value=baseline_fragments,
                    current_value=current_fragments,
                    change_percent=round(percent, 1),
                    severity=severity,
                )
            )
            if severity in ("degraded", "critical"):
                alerts.append(
                    "MFT fragmentation increased "
                    f"({baseline_fragments:.0f} → {current_fragments:.0f} fragments)"
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

    # Compare filesystem-pressure metrics if present. These are the primary
    # signals for cross-machine comparison (e.g. laptop vs desktop): tiny-file
    # burden and free-space headroom. Each tuple is
    # (key, higher_is_better, warn%, crit%, label, unit).
    _FS_METRICS = (
        ("tiny_files", False, 25.0, 50.0, "Tiny-file count", ""),
        ("tiny_file_ratio", False, 25.0, 50.0, "Tiny-file ratio", "%"),
        ("free_percent", True, 15.0, 30.0, "Free space", "%"),
    )
    for key, higher_is_better, warn, crit, label, unit in _FS_METRICS:
        if key not in baseline_data or key not in current_data:
            continue
        try:
            baseline_value = float(baseline_data[key])
            current_value = float(current_data[key])
        except (TypeError, ValueError):
            continue

        change = calculate_change(
            key,
            baseline_value,
            current_value,
            threshold_warning=warn,
            threshold_critical=crit,
            higher_is_better=higher_is_better,
        )
        changes.append(change)

        if change.severity in ("degraded", "critical"):
            direction = "decreased" if higher_is_better else "increased"
            alerts.append(
                f"{label} {direction} {abs(change.change_percent):.1f}% "
                f"({baseline_value:.1f}{unit} → {current_value:.1f}{unit})"
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
