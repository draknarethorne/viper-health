"""Tests for the machine-profile builder (cross-machine comparison)."""

import json

from viper_health.cli.profile_machine import (
    SCHEMA_VERSION,
    build_machine_profile,
    main,
)


def _make_tree(root):
    """Create a small tree: one tiny file, one large file, one subdir."""
    (root / "tiny.txt").write_bytes(b"x" * 10)  # tiny (<4096)
    (root / "big.bin").write_bytes(b"x" * 8192)  # not tiny
    sub = root / "sub"
    sub.mkdir()
    (sub / "tiny2.log").write_bytes(b"y" * 5)  # tiny


def test_build_machine_profile_core_metrics(tmp_path):
    """Profile captures machine info + flat comparable metrics."""
    _make_tree(tmp_path)

    profile = build_machine_profile(
        tmp_path,
        include_drives=False,
        include_trim=False,
        run_benchmark=False,
    )

    assert profile["schema_version"] == SCHEMA_VERSION
    assert profile["profile_type"] == "machine_profile"
    assert "timestamp" in profile

    machine = profile["machine"]
    for key in ("hostname", "os", "os_release", "python_version", "cpu_count"):
        assert key in machine

    # Flat comparable metrics used by compare_baseline.
    assert profile["total_files"] == 3
    assert profile["tiny_files"] == 2
    assert profile["tiny_file_ratio"] == round(2 / 3 * 100, 2)
    assert profile["directories_scanned"] >= 1
    assert profile["health_score"]["overall_score"] == 100.0
    assert profile["health_score"]["severity_band"] == "good"

    # Skipped collectors must not appear.
    assert "drives" not in profile
    assert "trim" not in profile
    assert "benchmark_results" not in profile


def test_build_machine_profile_is_json_serializable(tmp_path):
    """The full profile must serialize to JSON without custom encoders."""
    _make_tree(tmp_path)

    profile = build_machine_profile(
        tmp_path,
        include_drives=False,
        include_trim=False,
    )

    # Should not raise.
    text = json.dumps(profile)
    assert '"machine_profile"' in text


def test_build_machine_profile_empty_root_zero_ratio(tmp_path):
    """Empty root yields zero files and a zero tiny-file ratio (no div/0)."""
    profile = build_machine_profile(
        tmp_path,
        include_drives=False,
        include_trim=False,
    )

    assert profile["total_files"] == 0
    assert profile["tiny_files"] == 0
    assert profile["tiny_file_ratio"] == 0.0


def test_main_writes_profile_file(tmp_path):
    """CLI writes a JSON profile to the requested output path."""
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    _make_tree(scan_root)
    output = tmp_path / "profiles" / "TESTHOST.json"

    exit_code = main([
        str(scan_root),
        "--no-drives",
        "--no-trim",
        "--output",
        str(output),
    ])

    assert exit_code == 0
    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["profile_type"] == "machine_profile"
    assert data["total_files"] == 3


def test_main_missing_root_returns_error(tmp_path):
    """Nonexistent root path returns a nonzero exit code."""
    missing = tmp_path / "does-not-exist"
    exit_code = main([str(missing), "--no-drives", "--no-trim"])
    assert exit_code == 1
