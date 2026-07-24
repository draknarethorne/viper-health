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
    
    # Detailed recommendations
    if overall_severity != "good":
        print(f"{Fore.YELLOW}{Style.BRIGHT}💡 RECOMMENDATIONS & NEXT STEPS:{Style.RESET_ALL}\n")
        
        for result, assessment in zip(results, assessments):
            if assessment["severity"] == "critical":
                if result.pattern == "sequential" and result.operation == "write":
                    print(f"{Fore.RED}{Style.BRIGHT}🚨 CRITICAL: Sequential Write at {result.throughput_mb_s:.0f} MB/s{Style.RESET_ALL}")
                    print(f"   Expected for healthy SSD: >200 MB/s")
                    print(f"\n   {Style.BRIGHT}Likely Causes:{Style.RESET_ALL}")
                    print("   • SLC cache exhausted (drive overworked)")
                    print("   • Severe metadata pressure (tiny files, MFT fragmentation)")
                    print("   • Drive temperature throttling")
                    print("   • Insufficient free space (<20% remaining)")
                    print(f"\n   {Style.BRIGHT}Immediate Actions:{Style.RESET_ALL}")
                    print("   1. Check free space: Ensure >20% free (Windows needs headroom)")
                    print("   2. Run filesystem scan:")
                    print("      python -m viper_health.cli.suite --preset user-data --console-summary")
                    print("   3. Check MFT health (requires admin):")
                    print("      python -m viper_health.cli.scan_mft --drive C:")
                    print("   4. Let drive idle for 30+ minutes (TRIM/garbage collection)")
                    print("   5. Check drive temperature (HWiNFO64 or CrystalDiskInfo)")
                    print(f"\n   {Style.BRIGHT}Long-term Fixes:{Style.RESET_ALL}")
                    print("   • Clean up tiny-file hotspots (browser cache, temp files)")
                    print("   • Move large static files to secondary drive")
                    print("   • Disable indexing on high-churn folders")
                    print("   • Consider upgrading to SSD with DRAM cache")
                    print()
                
                elif result.pattern == "random" and result.operation == "write":
                    print(f"{Fore.RED}{Style.BRIGHT}🚨 CRITICAL: Random Write at {result.throughput_mb_s:.0f} MB/s{Style.RESET_ALL}")
                    print(f"   Expected for DRAM-less QLC: >20 MB/s")
                    print(f"\n   {Style.BRIGHT}Likely Causes:{Style.RESET_ALL}")
                    print("   • Extreme metadata pressure")
                    print("   • MFT severely fragmented")
                    print("   • Background processes hammering the drive")
                    print(f"\n   {Style.BRIGHT}Immediate Actions:{Style.RESET_ALL}")
                    print("   1. Identify background I/O:")
                    print("      - Open Resource Monitor → Disk tab")
                    print("      - Look for high I/O processes")
                    print("   2. Run MFT analysis (admin required):")
                    print("      python -m viper_health.cli.scan_mft --drive C:")
                    print("   3. Scan for tiny-file hotspots:")
                    print("      python -m viper_health.cli.suite --preset quick-check")
                    print()
            
            elif assessment["severity"] == "warning":
                if result.pattern == "sequential" and result.operation == "write":
                    print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  WARNING: Sequential Write at {result.throughput_mb_s:.0f} MB/s{Style.RESET_ALL}")
                    print(f"   Target for healthy performance: >200 MB/s")
                    print(f"\n   {Style.BRIGHT}What This Means:{Style.RESET_ALL}")
                    print("   • SLC cache partially full or under stress")
                    print("   • Moderate metadata pressure building")
                    print(f"\n   {Style.BRIGHT}Recommended Actions:{Style.RESET_ALL}")
                    print("   1. Run periodic filesystem scans to monitor trends:")
                    print("      python -m viper_health.cli.suite --preset user-data")
                    print("   2. Clean up temporary/cache files regularly")
                    print("   3. Let drive idle overnight for garbage collection")
                    print("   4. Re-run benchmark after idle period to compare")
                    print()
                
                elif result.pattern == "random" and result.operation == "write":
                    print(f"{Fore.YELLOW}{Style.BRIGHT}ℹ️  INFO: Random Write at {result.throughput_mb_s:.0f} MB/s{Style.RESET_ALL}")
                    print(f"   This is {Style.BRIGHT}typical{Style.RESET_ALL} for DRAM-less QLC SSDs")
                    print(f"\n   {Style.BRIGHT}Context:{Style.RESET_ALL}")
                    print("   • DRAM-less QLC SSDs have lower random write performance")
                    print("   • 20-50 MB/s is expected for this drive type")
                    print("   • Not necessarily a problem unless it degrades further")
                    print(f"\n   {Style.BRIGHT}Monitor for Changes:{Style.RESET_ALL}")
                    print("   • Run benchmarks weekly to track degradation")
                    print("   • If performance drops below 20 MB/s, investigate")
                    print()
        
        # General guidance
        print(f"{Fore.CYAN}{Style.BRIGHT}📋 GENERAL DRIVE HEALTH CHECKLIST:{Style.RESET_ALL}")
        print(f"   {Style.BRIGHT}After cleanup, allow 'calm phase' (30-60 minutes idle):{Style.RESET_ALL}")
        print("   • Windows runs TRIM commands to mark deleted blocks")
        print("   • SSD garbage collection reclaims space")
        print("   • SLC cache reorganizes and recovers capacity")
        print(f"\n   {Style.BRIGHT}Re-run benchmarks after calm phase:{Style.RESET_ALL}")
        print("   • Compare results to see if performance recovers")
        print("   • Save baseline: --output data/benchmarks/baseline.json")
        print(f"\n   {Style.BRIGHT}If performance remains poor:{Style.RESET_ALL}")
        print("   • Check TRIM status: fsutil behavior query DisableDeleteNotify")
        print("     (Should return: DisableDeleteNotify = 0 [TRIM enabled])")
        print("   • Check drive health: CrystalDiskInfo or smartctl")
        print("   • Monitor temperature: Should stay under 70°C")
        print()
    else:
        print(f"{Fore.GREEN}{Style.BRIGHT}✅ Excellent I/O Performance!{Style.RESET_ALL}")
        print("   Your SSD is performing well.")
        print("   Continue periodic monitoring to maintain health.")
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
