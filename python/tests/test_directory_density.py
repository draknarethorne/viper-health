"""
Tests for directory density analyzer.
"""

from pathlib import Path

from viper_health.analyzers.directory_density import analyze_directory_density
from viper_health.collectors.file_inventory import DirectoryStats, InventoryResult


def test_analyzer_flags_warning_and_critical(tmp_path: Path) -> None:
    """Verify severity classification for directory density."""
    # Create mock inventory with various density levels
    inventory = InventoryResult(
        root=str(tmp_path),
        tiny_file_max_bytes=4096,
        total_files=200_000,
        total_bytes=1_000_000,
        tiny_files=50_000,
        directories_scanned=3,
        per_directory={
            str(tmp_path / "low_density"): DirectoryStats(total_files=1_000, total_bytes=50_000, tiny_files=100),
            str(tmp_path / "warning_zone"): DirectoryStats(total_files=60_000, total_bytes=300_000, tiny_files=10_000),
            str(tmp_path / "critical_zone"): DirectoryStats(total_files=120_000, total_bytes=600_000, tiny_files=20_000),
        },
    )

    report = analyze_directory_density(
        inventory=inventory,
        warning_threshold=50_000,
        critical_threshold=100_000,
    )

    # Expect 2 findings: 1 warning, 1 critical
    assert len(report.findings) == 2
    assert report.warning_count == 1
    assert report.critical_count == 1

    # Verify severity assignment
    critical = [f for f in report.findings if f.severity == "critical"]
    warning = [f for f in report.findings if f.severity == "warning"]

    assert len(critical) == 1
    assert critical[0].path == tmp_path / "critical_zone"
    assert critical[0].total_files == 120_000

    assert len(warning) == 1
    assert warning[0].path == tmp_path / "warning_zone"
    assert warning[0].total_files == 60_000


def test_analyzer_suppresses_safe_path(tmp_path: Path) -> None:
    """Verify safe-path suppression behavior."""
    inventory = InventoryResult(
        root=str(tmp_path),
        tiny_file_max_bytes=4096,
        total_files=150_000,
        total_bytes=750_000,
        tiny_files=30_000,
        directories_scanned=2,
        per_directory={
            str(tmp_path / "safe" / "nested"): DirectoryStats(total_files=110_000, total_bytes=550_000, tiny_files=20_000),
            str(tmp_path / "unsafe"): DirectoryStats(total_files=70_000, total_bytes=350_000, tiny_files=15_000),
        },
    )

    safe_paths = [tmp_path / "safe"]

    report = analyze_directory_density(
        inventory=inventory,
        warning_threshold=50_000,
        critical_threshold=100_000,
        safe_paths=safe_paths,
    )

    # Expect 1 finding (unsafe), 1 suppressed (safe/nested)
    assert len(report.findings) == 1
    assert report.findings[0].path == tmp_path / "unsafe"

    assert len(report.suppressed) == 1
    assert report.suppressed[0].path == tmp_path / "safe" / "nested"
    assert report.suppressed[0].severity == "critical"


def test_analyzer_handles_empty_inventory(tmp_path: Path) -> None:
    """Verify behavior with empty inventory."""
    inventory = InventoryResult(
        root=str(tmp_path),
        tiny_file_max_bytes=4096,
        total_files=0,
        total_bytes=0,
        tiny_files=0,
        directories_scanned=0,
        per_directory={},
    )

    report = analyze_directory_density(inventory=inventory)

    assert len(report.findings) == 0
    assert len(report.suppressed) == 0
    assert report.total_directories_scanned == 0
    assert report.warning_count == 0
    assert report.critical_count == 0
