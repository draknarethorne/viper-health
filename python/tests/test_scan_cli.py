"""
Tests for unified scan CLI.
"""

from pathlib import Path

from viper_health.cli.scan import run_full_scan


def test_run_full_scan_integration(tmp_path: Path) -> None:
    """Verify full scan workflow integration."""
    # Create test directory structure
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    # Create some files
    for i in range(100):
        (test_dir / f"file_{i:04d}.txt").write_text("test content")

    # Run scan
    results = run_full_scan(
        root=test_dir,
        mode="observe",
        tiny_file_max_bytes=4096,
    )

    # Validate structure
    assert "mode" in results
    assert "scan_root" in results
    assert "inventory" in results
    assert "findings" in results
    assert "suppressed" in results
    assert "health_score" in results
    assert "recommendations" in results

    # Validate inventory
    assert results["inventory"].total_files >= 100
    assert results["inventory"].directories_scanned >= 1

    # Validate health score
    assert 0.0 <= results["health_score"].overall_score <= 100.0
    assert results["health_score"].severity_band in ["good", "watch", "degraded", "critical"]


def test_run_full_scan_with_safe_paths(tmp_path: Path) -> None:
    """Verify safe-path suppression in full scan."""
    # Create test directory
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()

    unsafe_dir = tmp_path / "unsafe"
    unsafe_dir.mkdir()

    # Create files in both
    for i in range(50):
        (safe_dir / f"file_{i}.txt").write_text("x")
        (unsafe_dir / f"file_{i}.txt").write_text("x")

    # Run scan with safe path
    results = run_full_scan(
        root=tmp_path,
        mode="observe",
        safe_paths=[safe_dir],
    )

    # Findings should not include safe_dir
    finding_paths = [f["path"] for f in results["findings"]]

    # Safe dir should be in suppressed, not findings
    assert not any(str(safe_dir) in p for p in finding_paths)
    # Note: Suppressed might be empty if thresholds aren't hit

    # Inventory should still count all files
    assert results["inventory"].total_files >= 100
