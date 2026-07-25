"""Tests for the machine-profile builder (cross-machine comparison)."""

import json
from unittest.mock import patch

from viper_health.analyzers.benchmark_preflight import BenchmarkPreflight
from viper_health.benchmarks.io_bench import BenchmarkResult
from viper_health.cli.profile_machine import (
    SCHEMA_VERSION,
    _summarize_benchmark_runs,
    build_machine_profile,
    main,
)
from viper_health.collectors.mft_info import MFTInfo
from viper_health.collectors.volume_info import VolumeInfo


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
    for key in (
        "hostname",
        "os",
        "os_release",
        "python_version",
        "cpu_count",
        "total_memory_bytes",
    ):
        assert key in machine

    # Flat comparable metrics used by compare_baseline.
    assert profile["total_files"] == 3
    assert profile["tiny_files"] == 2
    assert profile["tiny_file_ratio"] == round(2 / 3 * 100, 2)
    assert profile["directories_scanned"] >= 1
    assert profile["total_bytes"] == 8207
    assert profile["suppressed_findings_count"] == 0
    assert profile["finding_counts"] == {
        "warning": 0,
        "critical": 0,
        "tiny_file_hotspots": 0,
        "directory_density": 0,
    }
    assert profile["scan_config"]["tiny_file_max_bytes"] == 4096
    assert profile["health_score"]["overall_score"] == 100.0
    assert profile["health_score"]["severity_band"] == "good"

    # Skipped collectors must not appear.
    assert "drives" not in profile
    assert "volumes" not in profile
    assert "trim" not in profile
    assert "mft" not in profile
    assert "benchmark_results" not in profile


def _benchmark_result(test_name, throughput, iops, duration):
    operation = "write" if "write" in test_name else "read"
    pattern = "sequential" if "sequential" in test_name else "random"
    return BenchmarkResult(
        test_name=test_name,
        operation=operation,
        pattern=pattern,
        block_size=4096,
        total_bytes=409_600,
        duration_seconds=duration,
        throughput_mb_s=throughput,
        iops=iops,
    )


def test_summarize_benchmark_runs_uses_median_and_spread():
    """Repeated benchmarks preserve context and report robust statistics."""
    runs = [
        [_benchmark_result("random_write", 20.0, 5_000.0, 2.0)],
        [_benchmark_result("random_write", 40.0, 10_000.0, 1.0)],
        [_benchmark_result("random_write", 30.0, 7_500.0, 1.5)],
    ]

    summary = _summarize_benchmark_runs(runs)[0]

    assert summary["sample_count"] == 3
    assert summary["block_size"] == 4096
    assert summary["total_bytes"] == 409_600
    assert summary["throughput_mb_s"] == 30.0
    assert summary["throughput_mb_s_min"] == 20.0
    assert summary["throughput_mb_s_max"] == 40.0
    assert summary["throughput_mb_s_stdev"] == 8.16
    assert summary["iops"] == 7_500
    assert summary["duration_seconds"] == 1.5
    assert summary["severity"] == "info"


@patch("viper_health.collectors.volume_info.get_volume_info")
@patch("viper_health.collectors.mft_info.get_mft_info")
def test_build_machine_profile_storage_metrics(mock_mft, mock_volumes, tmp_path):
    """Schema v2 includes mounted-volume and MFT facts for comparisons."""
    mock_mft.return_value = MFTInfo("C:", 2_000_000_000, 3, 100, 20)
    mock_volumes.return_value = [
        VolumeInfo("C:", "System", "NTFS", "Fixed", "Healthy", 1000, 400, 40.0)
    ]

    profile = build_machine_profile(
        tmp_path,
        include_drives=False,
        include_trim=False,
        include_mft=True,
        include_volumes=True,
    )

    assert profile["mft_size_bytes"] == 2_000_000_000
    assert profile["mft_fragments"] == 3
    assert profile["mft"]["overall_severity"] == "good"
    assert profile["volumes"][0]["drive"] == "C:"
    assert profile["volumes"][0]["free_percent"] == 40.0


@patch("viper_health.cli.profile_machine.run_io_benchmark")
def test_build_machine_profile_repeats_benchmark(mock_benchmark, tmp_path):
    """Benchmark configuration and multi-run medians are serialized."""
    mock_benchmark.side_effect = [
        [_benchmark_result("sequential_write", 200.0, 50_000.0, 1.0)],
        [_benchmark_result("sequential_write", 180.0, 45_000.0, 1.1)],
        [_benchmark_result("sequential_write", 220.0, 55_000.0, 0.9)],
    ]

    allowed = BenchmarkPreflight(True, 30, (), "info", 0, 1, ())
    with patch(
        "viper_health.cli.profile_machine.run_benchmark_preflight",
        return_value=allowed,
    ):
        profile = build_machine_profile(
            tmp_path,
            include_drives=False,
            include_trim=False,
            run_benchmark=True,
            benchmark_size_mb=64,
            benchmark_block_size_kb=8,
            benchmark_runs=3,
        )

    assert mock_benchmark.call_count == 3
    assert profile["benchmark_config"]["test_file_size_mb"] == 64
    assert profile["benchmark_config"]["block_size_kb"] == 8
    assert profile["benchmark_config"]["runs"] == 3
    assert profile["benchmark_results"][0]["throughput_mb_s"] == 200.0
    assert profile["benchmark_results"][0]["iops"] == 50_000
    assert profile["benchmark_results"][0]["severity"] == "info"


@patch("viper_health.cli.profile_machine.run_io_benchmark")
def test_build_machine_profile_blocks_benchmark_before_write(mock_benchmark, tmp_path):
    blocked = BenchmarkPreflight(
        False,
        30,
        ("storage: 2 relevant events (critical)",),
        "critical",
        2,
        1,
        (),
    )
    with patch(
        "viper_health.cli.profile_machine.run_benchmark_preflight",
        return_value=blocked,
    ):
        profile = build_machine_profile(
            tmp_path,
            include_drives=False,
            include_trim=False,
            run_benchmark=True,
        )

    mock_benchmark.assert_not_called()
    assert profile["benchmark_preflight"]["allowed"] is False
    assert profile["benchmark_results"]["available"] is False


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
        "--no-mft",
        "--no-volumes",
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
