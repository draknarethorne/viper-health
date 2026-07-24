"""Analyzer for tiny-file hotspots based on inventory metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from viper_health.collectors.file_inventory import InventoryResult


@dataclass(frozen=True)
class TinyFileHotspot:
    """Classification result for a single directory."""

    path: Path
    tiny_files: int
    severity: str  # "warning" | "critical"


@dataclass(frozen=True)
class TinyFileHotspotReport:
    """Aggregated hotspot analysis output."""

    findings: tuple[TinyFileHotspot, ...]
    suppressed: tuple[TinyFileHotspot, ...]
    total_directories_scanned: int
    warning_count: int
    critical_count: int


def analyze_tiny_file_hotspots(
    inventory: InventoryResult,
    *,
    warning_threshold: int = 20_000,
    critical_threshold: int = 50_000,
    safe_paths: list[Path | str] | None = None,
) -> TinyFileHotspotReport:
    """Detect directories exceeding tiny-file thresholds.

    Directories in safe_paths are emitted as suppressed findings.
    """

    if warning_threshold <= 0:
        raise ValueError("warning_threshold must be > 0")
    if critical_threshold <= warning_threshold:
        raise ValueError("critical_threshold must be greater than warning_threshold")

    # Normalize safe paths
    safe_set = {Path(p).resolve() for p in safe_paths} if safe_paths else set()

    findings_list: list[TinyFileHotspot] = []
    suppressed_list: list[TinyFileHotspot] = []

    for directory_str, stats in sorted(inventory.per_directory.items()):
        if stats.tiny_files < warning_threshold:
            continue

        dir_path = Path(directory_str)
        severity = "critical" if stats.tiny_files >= critical_threshold else "warning"

        hotspot = TinyFileHotspot(
            path=dir_path,
            tiny_files=stats.tiny_files,
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
            suppressed_list.append(hotspot)
        else:
            findings_list.append(hotspot)

    # Sort by tiny_files descending
    findings_sorted = sorted(findings_list, key=lambda h: h.tiny_files, reverse=True)
    suppressed_sorted = sorted(suppressed_list, key=lambda h: h.tiny_files, reverse=True)

    warning_count = sum(1 for h in findings_sorted if h.severity == "warning")
    critical_count = sum(1 for h in findings_sorted if h.severity == "critical")

    return TinyFileHotspotReport(
        findings=tuple(findings_sorted),
        suppressed=tuple(suppressed_sorted),
        total_directories_scanned=inventory.directories_scanned,
        warning_count=warning_count,
        critical_count=critical_count,
    )
