"""Analyzer for tiny-file hotspots based on inventory metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from viper_health.collectors.file_inventory import InventoryResult


@dataclass(frozen=True)
class TinyFileHotspot:
    """Classification result for a single directory."""

    path: str
    tiny_files: int
    severity: str
    suppressed: bool
    reason: str | None = None


@dataclass(frozen=True)
class TinyFileHotspotReport:
    """Aggregated hotspot analysis output."""

    warning_threshold: int
    critical_threshold: int
    hotspots: list[TinyFileHotspot]


def _normalize_paths(paths: list[str] | None) -> set[str]:
    if not paths:
        return set()
    return {str(Path(path).resolve()) for path in paths}


def analyze_tiny_file_hotspots(
    inventory: InventoryResult,
    *,
    warning_threshold: int = 20_000,
    critical_threshold: int = 50_000,
    safe_paths: list[str] | None = None,
) -> TinyFileHotspotReport:
    """Detect directories exceeding tiny-file thresholds.

    Directories in safe_paths are emitted as suppressed findings.
    """

    if warning_threshold <= 0:
        raise ValueError("warning_threshold must be > 0")
    if critical_threshold <= warning_threshold:
        raise ValueError("critical_threshold must be greater than warning_threshold")

    normalized_safe_paths = _normalize_paths(safe_paths)
    findings: list[TinyFileHotspot] = []

    for directory, stats in sorted(inventory.per_directory.items()):
        if stats.tiny_files < warning_threshold:
            continue

        severity = "critical" if stats.tiny_files >= critical_threshold else "warning"
        suppressed = directory in normalized_safe_paths

        findings.append(
            TinyFileHotspot(
                path=directory,
                tiny_files=stats.tiny_files,
                severity=severity,
                suppressed=suppressed,
                reason="safe_path" if suppressed else None,
            )
        )

    return TinyFileHotspotReport(
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        hotspots=findings,
    )
