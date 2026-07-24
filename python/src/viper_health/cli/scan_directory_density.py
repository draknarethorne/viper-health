"""
CLI entrypoint for directory density scanning.

Usage:
    python -m viper_health.cli.scan_directory_density <root_path> [options]

Example:
    python -m viper_health.cli.scan_directory_density C:/Temp --warning-threshold 30000 --critical-threshold 80000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.analyzers.directory_density import analyze_directory_density
from viper_health.collectors.file_inventory import scan_file_inventory


def build_directory_density_report(
    root: Path,
    warning_threshold: int,
    critical_threshold: int,
    safe_paths: list[Path] | None,
) -> dict:
    """
    Build directory density report from scan.

    Returns:
        Dictionary with summary and findings suitable for JSON serialization
    """
    # Step 1: Collect inventory
    inventory = scan_file_inventory(root)

    # Step 2: Analyze directory density
    report = analyze_directory_density(
        inventory=inventory,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        safe_paths=safe_paths,
    )

    # Step 3: Build JSON-serializable report
    return {
        "summary": {
            "root": str(root),
            "total_directories_scanned": report.total_directories_scanned,
            "warning_count": report.warning_count,
            "critical_count": report.critical_count,
            "suppressed_count": len(report.suppressed),
        },
        "findings": [
            {
                "path": str(f.path),
                "total_files": f.total_files,
                "severity": f.severity,
            }
            for f in report.findings
        ],
        "suppressed": [
            {
                "path": str(f.path),
                "total_files": f.total_files,
                "severity": f.severity,
            }
            for f in report.suppressed
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Scan directory density (file counts per directory tree)",
        epilog="""
Examples:
  # Scan with default thresholds
  python -m viper_health.cli.scan_directory_density C:/Users/scott/AppData/Local

  # Scan with custom thresholds and save to JSON
  python -m viper_health.cli.scan_directory_density C:/Temp --warning-threshold 30000 --critical-threshold 80000 --output-json density.json

  # Scan with safe-path exclusions
  python -m viper_health.cli.scan_directory_density C:/ --safe-path "C:/Windows/System32"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Root directory to scan",
    )
    parser.add_argument(
        "--warning-threshold",
        type=int,
        default=50_000,
        help="File count threshold for warning severity (default: 50000)",
    )
    parser.add_argument(
        "--critical-threshold",
        type=int,
        default=100_000,
        help="File count threshold for critical severity (default: 100000)",
    )
    parser.add_argument(
        "--safe-path",
        type=Path,
        action="append",
        dest="safe_paths",
        help="Path to suppress from findings (can be specified multiple times)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write JSON report to file",
    )

    args = parser.parse_args(argv)

    # Validate root exists
    if not args.root.exists():
        print(f"Error: Root path does not exist: {args.root}", file=sys.stderr)
        return 1

    # Build report
    report = build_directory_density_report(
        root=args.root,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold,
        safe_paths=args.safe_paths,
    )

    # Output
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {args.output_json}")
    else:
        print(json.dumps(report, indent=2))

    # Exit code: 1 if critical findings, 0 otherwise
    return 1 if report["summary"]["critical_count"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
