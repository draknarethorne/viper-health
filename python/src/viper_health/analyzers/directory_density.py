"""
Directory density analyzer for viper-health.

Classifies directories by total file count (directory tree density).

Spec reference: Section 4.2 (Directory density)
- Warning: > 50,000 files
- Critical: > 100,000 files
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from viper_health.collectors.file_inventory import InventoryResult


@dataclass(frozen=True)
class DirectoryDensityFinding:
    """Single directory with elevated file count."""

    path: Path
    total_files: int
    severity: str  # "warning" | "critical"


@dataclass(frozen=True)
class DirectoryDensityReport:
    """Aggregate report of directory density findings."""

    findings: tuple[DirectoryDensityFinding, ...]
    suppressed: tuple[DirectoryDensityFinding, ...]
    total_directories_scanned: int
    warning_count: int
    critical_count: int


def analyze_directory_density(
    inventory: InventoryResult,
    warning_threshold: int = 50_000,
    critical_threshold: int = 100_000,
    safe_paths: Sequence[Path] | None = None,
) -> DirectoryDensityReport:
    """
    Analyze directory density from inventory results.

    Args:
        inventory: File inventory from collectors.file_inventory.scan_file_inventory
        warning_threshold: File count threshold for warning severity (default: 50,000)
        critical_threshold: File count threshold for critical severity (default: 100,000)
        safe_paths: Optional sequence of paths to suppress from findings

    Returns:
        DirectoryDensityReport with findings, suppressions, and counts
    """
    safe_set = {p.resolve() for p in safe_paths} if safe_paths else set()

    findings_list: list[DirectoryDensityFinding] = []
    suppressed_list: list[DirectoryDensityFinding] = []

    for dir_path_str, stats in inventory.per_directory.items():
        dir_path = Path(dir_path_str)
        total_files = stats.total_files

        # Determine severity
        if total_files >= critical_threshold:
            severity = "critical"
        elif total_files >= warning_threshold:
            severity = "warning"
        else:
            continue  # Below thresholds, skip

        finding = DirectoryDensityFinding(
            path=dir_path,
            total_files=total_files,
            severity=severity,
        )

        # Check if path is in safe set (exact match or parent match)
        is_safe = False
        resolved_dir = dir_path.resolve()
        for safe in safe_set:
            if resolved_dir == safe or safe in resolved_dir.parents:
                is_safe = True
                break

        if is_safe:
            suppressed_list.append(finding)
        else:
            findings_list.append(finding)

    # Sort by total_files descending for consistent output
    findings_sorted = sorted(findings_list, key=lambda f: f.total_files, reverse=True)
    suppressed_sorted = sorted(suppressed_list, key=lambda f: f.total_files, reverse=True)

    warning_count = sum(1 for f in findings_sorted if f.severity == "warning")
    critical_count = sum(1 for f in findings_sorted if f.severity == "critical")

    return DirectoryDensityReport(
        findings=tuple(findings_sorted),
        suppressed=tuple(suppressed_sorted),
        total_directories_scanned=inventory.directories_scanned,
        warning_count=warning_count,
        critical_count=critical_count,
    )
