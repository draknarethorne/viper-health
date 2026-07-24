"""
JSON report generator for viper-health.

Produces machine-readable JSON reports conforming to spec schema.

Spec reference: Section 7 (Output and Report Requirements)

Required top-level fields:
- timestamp_utc
- host
- mode
- scan_scope
- metrics
- findings
- suppressed_findings
- score
- recommendations
"""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from viper_health.scoring.health_score import HealthScore


def build_json_report(
    *,
    scan_root: Path,
    mode: str,
    total_files: int,
    tiny_files: int,
    directories_scanned: int,
    findings: list[dict[str, Any]],
    suppressed: list[dict[str, Any]],
    health_score: HealthScore | None = None,
    recommendations: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build JSON report structure.

    Args:
        scan_root: Root path scanned
        mode: Execution mode (observe/maintenance)
        total_files: Total file count
        tiny_files: Tiny file count
        directories_scanned: Directory count
        findings: List of detector findings
        suppressed: List of suppressed findings
        health_score: Optional HealthScore object
        recommendations: Optional list of recommended actions

    Returns:
        Dictionary suitable for JSON serialization
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    hostname = platform.node()

    report = {
        "timestamp_utc": timestamp,
        "host": hostname,
        "mode": mode,
        "scan_scope": {
            "root": str(scan_root),
            "total_files": total_files,
            "tiny_files": tiny_files,
            "directories_scanned": directories_scanned,
        },
        "metrics": {
            "tiny_file_ratio": tiny_files / total_files if total_files > 0 else 0.0,
        },
        "findings": findings,
        "suppressed_findings": suppressed,
    }

    if health_score:
        report["score"] = {
            "overall": health_score.overall_score,
            "severity_band": health_score.severity_band,
            "components": [
                {
                    "name": comp.name,
                    "score": comp.score,
                    "weight": comp.weight,
                    "weighted_contribution": comp.weighted_contribution,
                }
                for comp in health_score.components
            ],
        }

    if recommendations:
        report["recommendations"] = recommendations

    return report


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    """
    Write JSON report to file.

    Args:
        report: JSON-serializable report dictionary
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def format_json_string(report: dict[str, Any]) -> str:
    """
    Format report as indented JSON string.

    Args:
        report: JSON-serializable report dictionary

    Returns:
        Formatted JSON string
    """
    return json.dumps(report, indent=2)
