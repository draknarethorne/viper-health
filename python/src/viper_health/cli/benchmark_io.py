"""Safety-gated CLI for optional SSD I/O performance measurements."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.analyzers.benchmark_preflight import run_benchmark_preflight
from viper_health.benchmarks.io_bench import assess_benchmark_performance, run_io_benchmark


def _write_output(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run a benchmark only after passive evidence passes fail-closed checks."""
    parser = argparse.ArgumentParser(
        description="Optional I/O measurement with mandatory passive health preflight",
        epilog="""
A benchmark is not a hardware-health test. It is allowed only when Windows
System event coverage and drive reliability counters are available and contain
no unresolved warning or critical evidence. There is intentionally no override.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target", type=Path, help="Target directory (default: system temp)")
    parser.add_argument("--file-size", type=int, default=100, help="Test-file size in MB")
    parser.add_argument("--block-size", type=int, default=4, help="I/O block size in KiB")
    parser.add_argument("--preflight-days", type=int, default=30, help="Event lookback window")
    parser.add_argument("--output", type=Path, help="Save preflight and results as JSON")
    args = parser.parse_args(argv)

    if args.file_size < 1 or args.block_size < 1 or args.preflight_days < 1:
        parser.error("file size, block size, and preflight days must be at least 1")
    if args.target is not None and not args.target.is_dir():
        parser.error("--target must be an existing directory")

    preflight = run_benchmark_preflight(lookback_days=args.preflight_days)
    payload: dict = {
        "benchmark_type": "comparative_io_measurement",
        "preflight": preflight.to_dict(),
        "benchmark_config": {
            "target_dir": str(args.target) if args.target else "system_temp",
            "test_file_size_mb": args.file_size,
            "block_size_kib": args.block_size,
        },
        "results": [],
    }

    if not preflight.allowed:
        print("BENCHMARK BLOCKED BY PASSIVE HEALTH PREFLIGHT", file=sys.stderr)
        for reason in preflight.reasons:
            print(f"- {reason}", file=sys.stderr)
        print("No benchmark files were created.", file=sys.stderr)
        if args.output:
            _write_output(args.output, payload)
        return 2

    print("Passive health preflight passed. Running optional I/O measurement...")
    results = run_io_benchmark(
        target_dir=args.target,
        test_file_size_mb=args.file_size,
        block_size_kb=args.block_size,
    )
    payload["results"] = [
        {
            "test_name": result.test_name,
            "operation": result.operation,
            "pattern": result.pattern,
            "block_size": result.block_size,
            "total_bytes": result.total_bytes,
            "duration_seconds": result.duration_seconds,
            "throughput_mb_s": round(result.throughput_mb_s, 2),
            "iops": round(result.iops, 0),
            "assessment": assess_benchmark_performance(result),
        }
        for result in results
    ]

    for result in payload["results"]:
        print(
            f"{result['test_name']:<18} {result['throughput_mb_s']:>10.2f} MB/s "
            f"{result['iops']:>10.0f} IOPS"
        )
    print("Interpret these values only against a same-machine, same-configuration baseline.")
    if args.output:
        _write_output(args.output, payload)
        print(f"Results written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
