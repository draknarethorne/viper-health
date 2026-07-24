"""
Markdown report generator for viper-health.

Produces human-readable Markdown reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from viper_health.scoring.health_score import HealthScore


def build_markdown_report(
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
) -> str:
    """
    Build Markdown report string.

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
        Markdown-formatted report string
    """
    lines: list[str] = []

    # Header
    lines.append("# Viper Health Report")
    lines.append("")

    # Scan overview
    lines.append("## Scan Overview")
    lines.append("")
    lines.append(f"- **Root:** `{scan_root}`")
    lines.append(f"- **Mode:** {mode}")
    lines.append(f"- **Total files:** {total_files:,}")
    lines.append(f"- **Tiny files:** {tiny_files:,}")
    lines.append(f"- **Directories scanned:** {directories_scanned:,}")
    lines.append("")

    # Health score
    if health_score:
        lines.append("## Health Score")
        lines.append("")
        lines.append(f"- **Overall:** {health_score.overall_score:.1f} / 100")
        lines.append(f"- **Severity:** {health_score.severity_band.upper()}")
        lines.append("")

        if health_score.components:
            lines.append("### Component Scores")
            lines.append("")
            lines.append("| Component | Score | Weight | Contribution |")
            lines.append("|-----------|-------|--------|--------------|")
            for comp in health_score.components:
                lines.append(
                    f"| {comp.name} | {comp.score:.1f} | {comp.weight:.0f} | {comp.weighted_contribution:.2f} |"
                )
            lines.append("")

    # Findings
    lines.append("## Findings")
    lines.append("")
    if findings:
        lines.append(f"**{len(findings)} finding(s) detected:**")
        lines.append("")
        for i, finding in enumerate(findings, start=1):
            severity = finding.get("severity", "unknown").upper()
            path = finding.get("path", "N/A")
            count = finding.get("total_files") or finding.get("tiny_files") or "N/A"
            lines.append(f"{i}. **{severity}** - `{path}` ({count} files)")
        lines.append("")
    else:
        lines.append("No findings detected (all metrics within normal ranges).")
        lines.append("")

    # Suppressed findings
    if suppressed:
        lines.append("## Suppressed Findings")
        lines.append("")
        lines.append(f"**{len(suppressed)} finding(s) suppressed (safe paths):**")
        lines.append("")
        for i, finding in enumerate(suppressed, start=1):
            severity = finding.get("severity", "unknown").upper()
            path = finding.get("path", "N/A")
            count = finding.get("total_files") or finding.get("tiny_files") or "N/A"
            lines.append(f"{i}. {severity} - `{path}` ({count} files)")
        lines.append("")

    # Recommendations
    if recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)


def write_markdown_report(content: str, output_path: Path) -> None:
    """
    Write Markdown report to file.

    Args:
        content: Markdown report string
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
