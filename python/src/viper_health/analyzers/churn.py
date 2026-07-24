"""
Churn velocity analyzer (snapshot-over-snapshot).

Computes file/byte growth velocity and acceleration between two snapshots,
detecting churn per spec Section 4.4/4.5 (created/day) and Section 11
(velocity + acceleration, "new risk" vs "existing risk" labels).

Read-only: consumes snapshots, emits classification only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from viper_health.collectors.snapshot import Snapshot, SnapshotEntry


@dataclass(frozen=True)
class ChurnFinding:
    """Churn metrics for a single target between two snapshots."""

    name: str
    category: str
    path: str
    files_delta: int
    bytes_delta: int
    files_per_day: float
    bytes_per_day: float
    severity: str  # "good" | "warning" | "critical"
    risk_label: str  # "new" | "existing" | "resolved" | "stable"


@dataclass(frozen=True)
class ChurnReport:
    """Aggregate churn analysis between two snapshots."""

    previous_timestamp: str
    current_timestamp: str
    elapsed_days: float
    findings: tuple[ChurnFinding, ...]
    warning_count: int
    critical_count: int
    overall_severity: str


# Default churn thresholds (files created per day) from spec 4.4/4.5
DEFAULT_FILES_PER_DAY_WARNING = 10_000
DEFAULT_FILES_PER_DAY_CRITICAL = 25_000


def _elapsed_days(previous_ts: str, current_ts: str) -> float:
    """Compute elapsed days between two ISO timestamps (min 1 hour floor)."""
    try:
        prev = datetime.fromisoformat(previous_ts)
        curr = datetime.fromisoformat(current_ts)
        delta = (curr - prev).total_seconds()
    except (ValueError, TypeError):
        return 1.0

    days = delta / 86400.0
    # Floor to ~1 hour to avoid divide-by-tiny inflating velocity
    return max(days, 1.0 / 24.0)


def _index_entries(snapshot: Snapshot) -> dict[str, SnapshotEntry]:
    """Index snapshot entries by their path (case-insensitive)."""
    return {e.path.lower(): e for e in snapshot.entries}


def compute_churn(
    previous: Snapshot,
    current: Snapshot,
    *,
    files_per_day_warning: int = DEFAULT_FILES_PER_DAY_WARNING,
    files_per_day_critical: int = DEFAULT_FILES_PER_DAY_CRITICAL,
) -> ChurnReport:
    """
    Compute churn velocity between two snapshots.

    Args:
        previous: Earlier snapshot.
        current: Later snapshot.
        files_per_day_warning: Warning threshold for files created/day.
        files_per_day_critical: Critical threshold for files created/day.

    Returns:
        ChurnReport with per-target velocity and risk labels.
    """
    days = _elapsed_days(previous.timestamp_utc, current.timestamp_utc)
    prev_index = _index_entries(previous)
    curr_index = _index_entries(current)

    findings: list[ChurnFinding] = []

    # Union of all paths seen in either snapshot
    all_paths = set(prev_index) | set(curr_index)

    for path_key in all_paths:
        prev_entry = prev_index.get(path_key)
        curr_entry = curr_index.get(path_key)

        # Use whichever entry has identity metadata
        ref = curr_entry or prev_entry
        assert ref is not None

        prev_files = prev_entry.file_count if prev_entry else 0
        curr_files = curr_entry.file_count if curr_entry else 0
        prev_bytes = prev_entry.total_bytes if prev_entry else 0
        curr_bytes = curr_entry.total_bytes if curr_entry else 0

        files_delta = curr_files - prev_files
        bytes_delta = curr_bytes - prev_bytes

        files_per_day = files_delta / days
        bytes_per_day = bytes_delta / days

        # Severity based on absolute growth velocity (positive growth only)
        growth_rate = max(files_per_day, 0.0)
        if growth_rate >= files_per_day_critical:
            severity = "critical"
        elif growth_rate >= files_per_day_warning:
            severity = "warning"
        else:
            severity = "good"

        # Risk labeling
        if prev_entry is None and curr_entry is not None:
            risk_label = "new"
        elif files_delta > 0:
            risk_label = "existing"
        elif files_delta < 0:
            risk_label = "resolved"
        else:
            risk_label = "stable"

        findings.append(
            ChurnFinding(
                name=ref.name,
                category=ref.category,
                path=ref.path,
                files_delta=files_delta,
                bytes_delta=bytes_delta,
                files_per_day=round(files_per_day, 1),
                bytes_per_day=round(bytes_per_day, 1),
                severity=severity,
                risk_label=risk_label,
            )
        )

    # Sort: critical first, then by files_per_day descending
    severity_rank = {"critical": 0, "warning": 1, "good": 2}
    findings_sorted = sorted(
        findings,
        key=lambda f: (severity_rank[f.severity], -f.files_per_day),
    )

    warning_count = sum(1 for f in findings_sorted if f.severity == "warning")
    critical_count = sum(1 for f in findings_sorted if f.severity == "critical")

    if critical_count:
        overall = "critical"
    elif warning_count:
        overall = "warning"
    else:
        overall = "good"

    return ChurnReport(
        previous_timestamp=previous.timestamp_utc,
        current_timestamp=current.timestamp_utc,
        elapsed_days=round(days, 3),
        findings=tuple(findings_sorted),
        warning_count=warning_count,
        critical_count=critical_count,
        overall_severity=overall,
    )
