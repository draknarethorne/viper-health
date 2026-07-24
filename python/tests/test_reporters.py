"""
Tests for JSON and Markdown reporters.
"""

from pathlib import Path

from viper_health.reports.json_reporter import build_json_report, format_json_string
from viper_health.reports.markdown_reporter import build_markdown_report
from viper_health.scoring.health_score import (
    ComponentScore,
    HealthScore,
)


def test_json_reporter_minimal(tmp_path: Path) -> None:
    """Verify minimal JSON report structure."""
    report = build_json_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=[],
        suppressed=[],
    )

    # Validate required fields
    assert "timestamp_utc" in report
    assert "host" in report
    assert report["mode"] == "observe"
    assert report["scan_scope"]["root"] == str(tmp_path)
    assert report["scan_scope"]["total_files"] == 100
    assert report["findings"] == []
    assert report["suppressed_findings"] == []


def test_json_reporter_with_health_score(tmp_path: Path) -> None:
    """Verify JSON report with health score."""
    health_score = HealthScore(
        overall_score=85.5,
        severity_band="good",
        components=(
            ComponentScore(
                name="tiny_file_pressure",
                score=90.0,
                weight=20.0,
                weighted_contribution=18.0,
            ),
        ),
    )

    report = build_json_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=[],
        suppressed=[],
        health_score=health_score,
    )

    assert "score" in report
    assert report["score"]["overall"] == 85.5
    assert report["score"]["severity_band"] == "good"
    assert len(report["score"]["components"]) == 1


def test_json_reporter_format_string(tmp_path: Path) -> None:
    """Verify JSON string formatting."""
    report = build_json_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=[],
        suppressed=[],
    )

    json_str = format_json_string(report)
    assert isinstance(json_str, str)
    assert '"mode": "observe"' in json_str


def test_markdown_reporter_minimal(tmp_path: Path) -> None:
    """Verify minimal Markdown report structure."""
    md = build_markdown_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=[],
        suppressed=[],
    )

    assert "# Viper Health Report" in md
    assert "## Scan Overview" in md
    assert f"`{tmp_path}`" in md
    assert "observe" in md
    assert "No findings detected" in md


def test_markdown_reporter_with_findings(tmp_path: Path) -> None:
    """Verify Markdown report with findings."""
    findings = [
        {"severity": "critical", "path": "/tmp/test", "total_files": 10000},
        {"severity": "warning", "path": "/tmp/other", "total_files": 5000},
    ]

    md = build_markdown_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=findings,
        suppressed=[],
    )

    assert "## Findings" in md
    assert "2 finding(s) detected" in md
    assert "CRITICAL" in md
    assert "WARNING" in md


def test_markdown_reporter_with_health_score(tmp_path: Path) -> None:
    """Verify Markdown report with health score."""
    health_score = HealthScore(
        overall_score=72.3,
        severity_band="watch",
        components=(
            ComponentScore(
                name="tiny_file_pressure",
                score=70.0,
                weight=20.0,
                weighted_contribution=14.0,
            ),
        ),
    )

    md = build_markdown_report(
        scan_root=tmp_path,
        mode="observe",
        total_files=100,
        tiny_files=50,
        directories_scanned=10,
        findings=[],
        suppressed=[],
        health_score=health_score,
    )

    assert "## Health Score" in md
    assert "72.3" in md
    assert "WATCH" in md
    assert "### Component Scores" in md
