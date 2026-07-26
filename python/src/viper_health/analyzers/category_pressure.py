"""
Category pressure analyzer for churn/cache/residue detector families.

Scans well-known target roots (from collectors.target_roots) and classifies
each by file count and cumulative size against category thresholds.

Spec references:
- 4.4 Cloud-sync churn (tiny files in sync roots > 50,000)
- 4.5 Browser/WebView2 cache churn (file count > 50,000)
- 4.6 Update/installer residue (leftovers > 5 GiB, file count > 10,000)
- 4.7 Telemetry/log churn (log files > 10,000, cumulative > 5 GiB)

This analyzer is read-only. It reports pressure; it never mutates.
"""

from __future__ import annotations

from dataclasses import dataclass

from viper_health.collectors.target_roots import TargetRoot
from viper_health.utils.fs_counter import TreeCount, count_tree, format_bytes


@dataclass(frozen=True)
class CategoryThresholds:
    """Thresholds for classifying a target category."""

    file_count_warning: int
    file_count_critical: int
    size_warning_bytes: int
    size_critical_bytes: int


@dataclass(frozen=True)
class TargetFinding:
    """Classification result for a single target root."""

    name: str
    category: str
    path: str
    file_count: int
    total_bytes: int
    tiny_files: int
    severity: str  # "good" | "warning" | "critical"
    reason: str


@dataclass(frozen=True)
class CategoryReport:
    """Aggregate report for a detector category."""

    category: str
    findings: tuple[TargetFinding, ...]
    total_files: int
    total_bytes: int
    total_tiny_files: int
    good_count: int
    warning_count: int
    critical_count: int
    overall_severity: str


# Default thresholds per category (derived from spec Section 4)
DEFAULT_THRESHOLDS: dict[str, CategoryThresholds] = {
    "cloud_sync": CategoryThresholds(
        file_count_warning=50_000,
        file_count_critical=100_000,
        size_warning_bytes=10 * 1024**3,
        size_critical_bytes=25 * 1024**3,
    ),
    "browser_cache": CategoryThresholds(
        file_count_warning=50_000,
        file_count_critical=100_000,
        size_warning_bytes=5 * 1024**3,
        size_critical_bytes=15 * 1024**3,
    ),
    "update_residue": CategoryThresholds(
        file_count_warning=10_000,
        file_count_critical=30_000,
        size_warning_bytes=5 * 1024**3,
        size_critical_bytes=15 * 1024**3,
    ),
    "telemetry_log": CategoryThresholds(
        file_count_warning=10_000,
        file_count_critical=30_000,
        size_warning_bytes=5 * 1024**3,
        size_critical_bytes=15 * 1024**3,
    ),
}


def _classify(
    count: TreeCount,
    thresholds: CategoryThresholds,
) -> tuple[str, str]:
    """Return (severity, reason) for a tree count against thresholds."""
    reasons: list[str] = []
    severity = "good"

    # File-count dimension
    if count.file_count >= thresholds.file_count_critical:
        severity = "critical"
        reasons.append(
            f"{count.file_count:,} files >= critical {thresholds.file_count_critical:,}"
        )
    elif count.file_count >= thresholds.file_count_warning:
        if severity != "critical":
            severity = "warning"
        reasons.append(
            f"{count.file_count:,} files >= warning {thresholds.file_count_warning:,}"
        )

    # Size dimension
    if count.total_bytes >= thresholds.size_critical_bytes:
        severity = "critical"
        reasons.append(
            f"{format_bytes(count.total_bytes)} >= critical "
            f"{format_bytes(thresholds.size_critical_bytes)}"
        )
    elif count.total_bytes >= thresholds.size_warning_bytes:
        if severity != "critical":
            severity = "warning"
        reasons.append(
            f"{format_bytes(count.total_bytes)} >= warning "
            f"{format_bytes(thresholds.size_warning_bytes)}"
        )

    reason = "; ".join(reasons) if reasons else "within normal thresholds"
    return severity, reason


def analyze_category(
    category: str,
    roots: list[TargetRoot],
    *,
    thresholds: CategoryThresholds | None = None,
    tiny_file_max_bytes: int = 4096,
) -> CategoryReport:
    """
    Scan and classify all target roots for a category.

    Args:
        category: Category identifier (matches DEFAULT_THRESHOLDS keys).
        roots: Target roots to scan (typically from target_roots collector).
        thresholds: Optional override thresholds; defaults to category defaults.
        tiny_file_max_bytes: Tiny-file classification threshold.

    Returns:
        CategoryReport with per-root findings and aggregate severity.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.get(
            category,
            CategoryThresholds(50_000, 100_000, 5 * 1024**3, 15 * 1024**3),
        )

    findings: list[TargetFinding] = []
    total_files = 0
    total_bytes = 0
    total_tiny = 0

    for root in roots:
        if not root.exists:
            continue

        count = count_tree(root.path, tiny_file_max_bytes=tiny_file_max_bytes)
        severity, reason = _classify(count, thresholds)

        findings.append(
            TargetFinding(
                name=root.name,
                category=category,
                path=str(root.path),
                file_count=count.file_count,
                total_bytes=count.total_bytes,
                tiny_files=count.tiny_files,
                severity=severity,
                reason=reason,
            )
        )

        total_files += count.file_count
        total_bytes += count.total_bytes
        total_tiny += count.tiny_files

    # Sort findings by severity (critical first) then file count
    severity_rank = {"critical": 0, "warning": 1, "good": 2}
    findings_sorted = sorted(
        findings,
        key=lambda f: (severity_rank[f.severity], -f.file_count),
    )

    good_count = sum(1 for f in findings_sorted if f.severity == "good")
    warning_count = sum(1 for f in findings_sorted if f.severity == "warning")
    critical_count = sum(1 for f in findings_sorted if f.severity == "critical")

    if critical_count:
        overall = "critical"
    elif warning_count:
        overall = "warning"
    else:
        overall = "good"

    return CategoryReport(
        category=category,
        findings=tuple(findings_sorted),
        total_files=total_files,
        total_bytes=total_bytes,
        total_tiny_files=total_tiny,
        good_count=good_count,
        warning_count=warning_count,
        critical_count=critical_count,
        overall_severity=overall,
    )
