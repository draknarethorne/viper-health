"""
Optional I/O performance measurement utilities.

Measurements are intended for same-machine baseline comparisons. Absolute
throughput cannot diagnose media health or infer NAND type, DRAM, cache state,
temperature, or a root cause.
"""

from __future__ import annotations

import os
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkResult:
    """Results from a single I/O benchmark test."""

    test_name: str
    operation: str  # "read" or "write"
    pattern: str  # "sequential" or "random"
    block_size: int  # bytes
    total_bytes: int
    duration_seconds: float
    throughput_mb_s: float
    iops: float


def assess_benchmark_performance(result: BenchmarkResult) -> dict[str, object]:
    """Describe a measurement without turning it into a health diagnosis.

    A valid positive result is informational. Degradation classification belongs
    in baseline comparison where hardware, block size, workload, and machine
    context can be held constant.
    """
    valid = (
        result.throughput_mb_s > 0
        and result.iops > 0
        and result.duration_seconds > 0
    )
    return {
        "severity": "info" if valid else "critical",
        "message": (
            "Measurement captured; compare with a same-machine, same-configuration baseline."
            if valid
            else "Invalid benchmark measurement; do not infer hardware health."
        ),
        "throughput_mb_s": round(result.throughput_mb_s, 2),
        "iops": round(result.iops, 0),
    }


class IOBenchmarkSuite:
    """SSD I/O performance benchmark suite."""

    def __init__(
        self,
        *,
        target_dir: Path | None = None,
        test_file_size_mb: int = 100,
        block_size_kb: int = 4,
    ):
        """
        Initialize benchmark suite.

        Args:
            target_dir: Directory to run benchmarks in (default: temp)
            test_file_size_mb: Size of test file in MB
            block_size_kb: I/O block size in KB
        """
        self.target_dir = Path(target_dir) if target_dir else Path(tempfile.gettempdir())
        self.test_file_size_mb = test_file_size_mb
        self.block_size_kb = block_size_kb
        self.block_size = block_size_kb * 1024

    def sequential_write(self) -> BenchmarkResult:
        """Benchmark sequential write performance."""
        test_file = self.target_dir / f"viper_bench_seq_write_{os.getpid()}.tmp"
        total_bytes = self.test_file_size_mb * 1024 * 1024

        try:
            data = b"V" * self.block_size
            blocks_to_write = total_bytes // self.block_size

            start_time = time.perf_counter()

            with open(test_file, "wb", buffering=0) as f:
                for _ in range(blocks_to_write):
                    f.write(data)
                f.flush()
                os.fsync(f.fileno())

            duration = time.perf_counter() - start_time
            throughput = (total_bytes / (1024 * 1024)) / duration
            iops = blocks_to_write / duration

            return BenchmarkResult(
                test_name="sequential_write",
                operation="write",
                pattern="sequential",
                block_size=self.block_size,
                total_bytes=total_bytes,
                duration_seconds=duration,
                throughput_mb_s=throughput,
                iops=iops,
            )
        finally:
            if test_file.exists():
                test_file.unlink()

    def sequential_read(self) -> BenchmarkResult:
        """Benchmark sequential read performance."""
        test_file = self.target_dir / f"viper_bench_seq_read_{os.getpid()}.tmp"
        total_bytes = self.test_file_size_mb * 1024 * 1024

        try:
            # Create test file
            data = b"V" * self.block_size
            blocks = total_bytes // self.block_size

            with open(test_file, "wb") as f:
                for _ in range(blocks):
                    f.write(data)

            # Benchmark read
            start_time = time.perf_counter()

            with open(test_file, "rb", buffering=0) as f:
                while f.read(self.block_size):
                    pass

            duration = time.perf_counter() - start_time
            throughput = (total_bytes / (1024 * 1024)) / duration
            iops = blocks / duration

            return BenchmarkResult(
                test_name="sequential_read",
                operation="read",
                pattern="sequential",
                block_size=self.block_size,
                total_bytes=total_bytes,
                duration_seconds=duration,
                throughput_mb_s=throughput,
                iops=iops,
            )
        finally:
            if test_file.exists():
                test_file.unlink()

    def random_write(self, num_operations: int = 1000) -> BenchmarkResult:
        """Benchmark random write performance."""
        test_file = self.target_dir / f"viper_bench_rand_write_{os.getpid()}.tmp"
        file_size = self.test_file_size_mb * 1024 * 1024

        try:
            # Pre-allocate file
            with open(test_file, "wb") as f:
                f.write(b"\x00" * file_size)

            data = b"V" * self.block_size
            max_offset = file_size - self.block_size

            start_time = time.perf_counter()

            with open(test_file, "r+b", buffering=0) as f:
                for _ in range(num_operations):
                    offset = random.randint(0, max_offset // self.block_size) * self.block_size
                    f.seek(offset)
                    f.write(data)
                f.flush()
                os.fsync(f.fileno())

            duration = time.perf_counter() - start_time
            total_bytes = num_operations * self.block_size
            throughput = (total_bytes / (1024 * 1024)) / duration
            iops = num_operations / duration

            return BenchmarkResult(
                test_name="random_write",
                operation="write",
                pattern="random",
                block_size=self.block_size,
                total_bytes=total_bytes,
                duration_seconds=duration,
                throughput_mb_s=throughput,
                iops=iops,
            )
        finally:
            if test_file.exists():
                test_file.unlink()

    def random_read(self, num_operations: int = 1000) -> BenchmarkResult:
        """Benchmark random read performance."""
        test_file = self.target_dir / f"viper_bench_rand_read_{os.getpid()}.tmp"
        file_size = self.test_file_size_mb * 1024 * 1024

        try:
            # Create test file with data
            with open(test_file, "wb") as f:
                data = b"V" * self.block_size
                blocks = file_size // self.block_size
                for _ in range(blocks):
                    f.write(data)

            max_offset = file_size - self.block_size

            start_time = time.perf_counter()

            with open(test_file, "rb", buffering=0) as f:
                for _ in range(num_operations):
                    offset = random.randint(0, max_offset // self.block_size) * self.block_size
                    f.seek(offset)
                    f.read(self.block_size)

            duration = time.perf_counter() - start_time
            total_bytes = num_operations * self.block_size
            throughput = (total_bytes / (1024 * 1024)) / duration
            iops = num_operations / duration

            return BenchmarkResult(
                test_name="random_read",
                operation="read",
                pattern="random",
                block_size=self.block_size,
                total_bytes=total_bytes,
                duration_seconds=duration,
                throughput_mb_s=throughput,
                iops=iops,
            )
        finally:
            if test_file.exists():
                test_file.unlink()

    def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmark tests."""
        return [
            self.sequential_write(),
            self.sequential_read(),
            self.random_write(),
            self.random_read(),
        ]


def run_io_benchmark(
    target_dir: Path | None = None,
    *,
    test_file_size_mb: int = 100,
    block_size_kb: int = 4,
) -> list[BenchmarkResult]:
    """
    Run complete I/O benchmark suite.

    Args:
        target_dir: Directory to run benchmarks in (default: temp)
        test_file_size_mb: Size of test file in MB
        block_size_kb: I/O block size in KB

    Returns:
        List of benchmark results
    """
    suite = IOBenchmarkSuite(
        target_dir=target_dir,
        test_file_size_mb=test_file_size_mb,
        block_size_kb=block_size_kb,
    )
    return suite.run_all()
