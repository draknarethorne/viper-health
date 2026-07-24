"""CLI for running SSD I/O benchmarks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.benchmarks.io_bench import assess_benchmark_performance, run_io_benchmark

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for I/O benchmarks."""
    parser = argparse.ArgumentParser(
        description="Viper Health SSD I/O Performance Benchmarks",
        epilog="""
Examples:
  # Run benchmarks on default temp directory
  python -m viper_health.cli.benchmark_io

  # Run benchmarks on specific drive
  python -m viper_health.cli.benchmark_io --target D:\\

  # Larger test file for more accurate results
  python -m viper_health.cli.benchmark_io --file-size 500 --output bench.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--target",
        type=Path,
        help="Target directory for benchmark tests (default: system temp)",
    )
    
    parser.add_argument(
        "--file-size",
        type=int,
        default=100,
        help="Test file size in MB (default: 100)",
    )
    
    parser.add_argument(
        "--block-size",
        type=int,
        default=4,
        help="I/O block size in KB (default: 4)",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )
    
    args = parser.parse_args(argv)
    
    # Run benchmarks
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 Running I/O Benchmarks...{Style.RESET_ALL}\n")
    
    if args.target:
        print(f"Target: {args.target}")
    else:
        print("Target: System temp directory")
    
    print(f"Test file size: {args.file_size} MB")
    print(f"Block size: {args.block_size} KB")
    print()
    
    results = run_io_benchmark(
        target_dir=args.target,
        test_file_size_mb=args.file_size,
        block_size_kb=args.block_size,
    )
    
    # Analyze results
    assessments = [assess_benchmark_performance(r) for r in results]
    
    # Determine overall health
    critical_count = sum(1 for a in assessments if a["severity"] == "critical")
    warning_count = sum(1 for a in assessments if a["severity"] == "warning")
    
    if critical_count > 0:
        overall_severity = "critical"
        overall_icon = "❌"
        overall_color = Fore.RED
    elif warning_count > 1:
        overall_severity = "warning"
        overall_icon = "⚠️"
        overall_color = Fore.YELLOW
    else:
        overall_severity = "good"
        overall_icon = "✅"
        overall_color = Fore.GREEN
    
    # Display results
    print("="*70)
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 BENCHMARK RESULTS{Style.RESET_ALL}")
    print("="*70)
    
    for result, assessment in zip(results, assessments):
        # Determine status color and icon
        if assessment["severity"] == "good":
            status_color = Fore.GREEN
            status_icon = "✅"
        elif assessment["severity"] == "warning":
            status_color = Fore.YELLOW
            status_icon = "⚠️"
        else:  # critical
            status_color = Fore.RED
            status_icon = "❌"
        
        print(f"\n{Style.BRIGHT}{result.test_name.replace('_', ' ').title()}{Style.RESET_ALL}")
        print(f"  Operation: {result.operation} | Pattern: {result.pattern}")
        print(f"  Block Size: {result.block_size:,} bytes | Total: {result.total_bytes / (1024*1024):.1f} MB")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        print(f"  {status_color}{Style.BRIGHT}Throughput: {result.throughput_mb_s:.2f} MB/s{Style.RESET_ALL}")
        print(f"  IOPS: {result.iops:.0f}")
        print(f"  {status_color}{Style.BRIGHT}{status_icon} Status: {assessment['severity'].upper()}{Style.RESET_ALL}")
        print(f"  {Style.DIM}{assessment['message']}{Style.RESET_ALL}")
    
    print("\n" + "="*70)
    print(f"{overall_color}{Style.BRIGHT}{overall_icon} Overall I/O Health: {overall_severity.upper()}{Style.RESET_ALL}")
    print("="*70 + "\n")
    
    # Recommendations
    if overall_severity != "good":
        print(f"{Fore.YELLOW}{Style.BRIGHT}💡 Recommendations:{Style.RESET_ALL}")
        
        for result, assessment in zip(results, assessments):
            if assessment["severity"] == "critical":
                if result.pattern == "sequential" and result.operation == "write":
                    print(f"  • {Fore.RED}Critical:{Style.RESET_ALL} Sequential write at {result.throughput_mb_s:.0f} MB/s")
                    print("    - SLC cache likely exhausted")
                    print("    - High metadata pressure (tiny files, fragmentation)")
                    print("    - Run filesystem health scan to identify hotspots")
                elif result.pattern == "random" and result.operation == "write":
                    print(f"  • {Fore.RED}Critical:{Style.RESET_ALL} Random write at {result.throughput_mb_s:.0f} MB/s")
                    print("    - DRAM-less QLC showing severe degradation")
                    print("    - Reduce file churn and tiny-file pressure")
            
            elif assessment["severity"] == "warning":
                if result.pattern == "sequential" and result.operation == "write":
                    print(f"  • {Fore.YELLOW}Warning:{Style.RESET_ALL} Sequential write at {result.throughput_mb_s:.0f} MB/s")
                    print("    - Performance degrading, monitor filesystem health")
                elif result.pattern == "random" and result.operation == "write":
                    print(f"  • {Fore.YELLOW}Note:{Style.RESET_ALL} Random write at {result.throughput_mb_s:.0f} MB/s")
                    print("    - Typical for DRAM-less QLC SSDs")
        
        print()
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            "benchmark_config": {
                "target_dir": str(args.target) if args.target else "temp",
                "test_file_size_mb": args.file_size,
                "block_size_kb": args.block_size,
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "operation": r.operation,
                    "pattern": r.pattern,
                    "block_size": r.block_size,
                    "total_bytes": r.total_bytes,
                    "duration_seconds": r.duration_seconds,
                    "throughput_mb_s": round(r.throughput_mb_s, 2),
                    "iops": round(r.iops, 0),
                }
                for r in results
            ],
        }
        
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
