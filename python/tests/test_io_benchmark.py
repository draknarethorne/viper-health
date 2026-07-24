"""Tests for SSD I/O benchmark module."""

from pathlib import Path

import pytest

from viper_health.benchmarks.io_bench import (
    BenchmarkResult,
    IOBenchmarkSuite,
    assess_benchmark_performance,
    run_io_benchmark,
)


def test_benchmark_result_creation():
    """Test BenchmarkResult dataclass creation."""
    result = BenchmarkResult(
        test_name="test",
        operation="read",
        pattern="sequential",
        block_size=4096,
        total_bytes=1024*1024,
        duration_seconds=1.0,
        throughput_mb_s=1.0,
        iops=256.0,
    )
    
    assert result.test_name == "test"
    assert result.operation == "read"
    assert result.pattern == "sequential"
    assert result.throughput_mb_s == 1.0


def test_io_benchmark_suite_init(tmp_path):
    """Test IOBenchmarkSuite initialization."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=10,
        block_size_kb=4,
    )
    
    assert suite.target_dir == tmp_path
    assert suite.test_file_size_mb == 10
    assert suite.block_size_kb == 4
    assert suite.block_size == 4096


def test_sequential_write_benchmark(tmp_path):
    """Test sequential write benchmark."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=1,  # Small file for fast tests
        block_size_kb=4,
    )
    
    result = suite.sequential_write()
    
    assert result.test_name == "sequential_write"
    assert result.operation == "write"
    assert result.pattern == "sequential"
    assert result.total_bytes == 1024 * 1024
    assert result.duration_seconds > 0
    assert result.throughput_mb_s > 0
    assert result.iops > 0
    
    # Ensure cleanup happened
    assert not any(tmp_path.glob("viper_bench_seq_write_*.tmp"))


def test_sequential_read_benchmark(tmp_path):
    """Test sequential read benchmark."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=1,
        block_size_kb=4,
    )
    
    result = suite.sequential_read()
    
    assert result.test_name == "sequential_read"
    assert result.operation == "read"
    assert result.pattern == "sequential"
    assert result.total_bytes == 1024 * 1024
    assert result.duration_seconds > 0
    assert result.throughput_mb_s > 0
    
    # Ensure cleanup happened
    assert not any(tmp_path.glob("viper_bench_seq_read_*.tmp"))


def test_random_write_benchmark(tmp_path):
    """Test random write benchmark."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=1,
        block_size_kb=4,
    )
    
    result = suite.random_write(num_operations=100)  # Fewer ops for speed
    
    assert result.test_name == "random_write"
    assert result.operation == "write"
    assert result.pattern == "random"
    assert result.total_bytes == 100 * 4096
    assert result.duration_seconds > 0
    assert result.iops > 0
    
    # Ensure cleanup happened
    assert not any(tmp_path.glob("viper_bench_rand_write_*.tmp"))


def test_random_read_benchmark(tmp_path):
    """Test random read benchmark."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=1,
        block_size_kb=4,
    )
    
    result = suite.random_read(num_operations=100)
    
    assert result.test_name == "random_read"
    assert result.operation == "read"
    assert result.pattern == "random"
    assert result.total_bytes == 100 * 4096
    assert result.duration_seconds > 0
    assert result.iops > 0
    
    # Ensure cleanup happened
    assert not any(tmp_path.glob("viper_bench_rand_read_*.tmp"))


def test_run_all_benchmarks(tmp_path):
    """Test running all benchmarks in suite."""
    suite = IOBenchmarkSuite(
        target_dir=tmp_path,
        test_file_size_mb=1,
        block_size_kb=4,
    )
    
    results = suite.run_all()
    
    assert len(results) == 4
    assert results[0].test_name == "sequential_write"
    assert results[1].test_name == "sequential_read"
    assert results[2].test_name == "random_write"
    assert results[3].test_name == "random_read"
    
    # All should have positive metrics
    for result in results:
        assert result.duration_seconds > 0
        assert result.throughput_mb_s > 0
        assert result.iops > 0


def test_run_io_benchmark_helper(tmp_path):
    """Test run_io_benchmark helper function."""
    results = run_io_benchmark(
        target_dir=tmp_path,
        test_file_size_mb=1,
        block_size_kb=4,
    )
    
    assert len(results) == 4
    assert all(isinstance(r, BenchmarkResult) for r in results)


def test_assess_benchmark_performance_good():
    """Test benchmark performance assessment with good metrics."""
    result = BenchmarkResult(
        test_name="sequential_write",
        operation="write",
        pattern="sequential",
        block_size=4096,
        total_bytes=100*1024*1024,
        duration_seconds=0.5,
        throughput_mb_s=250.0,  # Good performance
        iops=64000.0,
    )
    
    assessment = assess_benchmark_performance(result)
    
    assert assessment["severity"] == "good"
    assert "SLC cache healthy" in assessment["message"]


def test_assess_benchmark_performance_warning():
    """Test benchmark performance assessment with warning metrics."""
    result = BenchmarkResult(
        test_name="sequential_write",
        operation="write",
        pattern="sequential",
        block_size=4096,
        total_bytes=100*1024*1024,
        duration_seconds=1.0,
        throughput_mb_s=150.0,  # Warning performance
        iops=38400.0,
    )
    
    assessment = assess_benchmark_performance(result)
    
    assert assessment["severity"] == "warning"
    assert "cache may be filling" in assessment["message"]


def test_assess_benchmark_performance_critical():
    """Test benchmark performance assessment with critical metrics."""
    result = BenchmarkResult(
        test_name="sequential_write",
        operation="write",
        pattern="sequential",
        block_size=4096,
        total_bytes=100*1024*1024,
        duration_seconds=2.0,
        throughput_mb_s=50.0,  # Critical performance
        iops=12800.0,
    )
    
    assessment = assess_benchmark_performance(result)
    
    assert assessment["severity"] == "critical"
    assert "SLC cache exhausted" in assessment["message"] or "metadata pressure" in assessment["message"]


def test_assess_random_write_dram_less_qlc():
    """Test random write assessment for typical DRAM-less QLC performance."""
    result = BenchmarkResult(
        test_name="random_write",
        operation="write",
        pattern="random",
        block_size=4096,
        total_bytes=4*1024*1024,
        duration_seconds=0.2,
        throughput_mb_s=35.0,  # Typical for DRAM-less QLC
        iops=8960.0,
    )
    
    assessment = assess_benchmark_performance(result)
    
    assert assessment["severity"] == "warning"
    assert "DRAM-less QLC" in assessment["message"]
