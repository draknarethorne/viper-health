"""
Tests for directory density CLI.
"""

from pathlib import Path

from viper_health.cli.scan_directory_density import build_directory_density_report


def test_build_directory_density_report_contains_summary_and_findings(tmp_path: Path) -> None:
    """Verify report structure from build_directory_density_report."""
    # Create test directory with some files
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    # Create enough files to trigger warning threshold
    for i in range(60):
        (test_dir / f"file_{i:04d}.txt").write_text("content")

    report = build_directory_density_report(
        root=test_dir,
        warning_threshold=50,
        critical_threshold=100,
        safe_paths=None,
    )

    # Validate structure
    assert "summary" in report
    assert "findings" in report
    assert "suppressed" in report

    # Validate summary keys
    summary = report["summary"]
    assert "root" in summary
    assert "total_directories_scanned" in summary
    assert "warning_count" in summary
    assert "critical_count" in summary
    assert "suppressed_count" in summary

    # Validate findings structure
    assert isinstance(report["findings"], list)
    if len(report["findings"]) > 0:
        finding = report["findings"][0]
        assert "path" in finding
        assert "total_files" in finding
        assert "severity" in finding
