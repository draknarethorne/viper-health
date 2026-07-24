"""CLI for tiny-file hotspot analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from viper_health.analyzers.tiny_file_hotspots import analyze_tiny_file_hotspots
from viper_health.collectors.file_inventory import InventoryResult, scan_file_inventory


def build_tiny_file_report(
    inventory: InventoryResult,
    *,
    warning_threshold: int,
    critical_threshold: int,
    safe_paths: list[Path] | None,
) -> dict:
    """Build a serializable report dictionary."""

    analysis = analyze_tiny_file_hotspots(
        inventory,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        safe_paths=safe_paths,
    )

    findings = [
        {
            "path": str(finding.path),
            "tiny_files": finding.tiny_files,
            "severity": finding.severity,
        }
        for finding in analysis.findings
    ]

    suppressed = [
        {
            "path": str(finding.path),
            "tiny_files": finding.tiny_files,
            "severity": finding.severity,
        }
        for finding in analysis.suppressed
    ]

    return {
        "root": inventory.root,
        "tiny_file_max_bytes": inventory.tiny_file_max_bytes,
        "summary": {
            "total_files": inventory.total_files,
            "tiny_files": inventory.tiny_files,
            "total_bytes": inventory.total_bytes,
            "directories_scanned": inventory.directories_scanned,
            "warning_count": analysis.warning_count,
            "critical_count": analysis.critical_count,
            "suppressed_count": len(analysis.suppressed),
        },
        "findings": findings,
        "suppressed": suppressed,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan for tiny-file hotspot directories")
    parser.add_argument("root", help="Root directory to scan")
    parser.add_argument("--tiny-max-bytes", type=int, default=4096)
    parser.add_argument("--warning-threshold", type=int, default=20_000)
    parser.add_argument("--critical-threshold", type=int, default=50_000)
    parser.add_argument("--safe-path", action="append", dest="safe_paths", default=[])
    parser.add_argument("--output-json", type=str, default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    inventory = scan_file_inventory(Path(args.root), tiny_file_max_bytes=args.tiny_max_bytes)
    report = build_tiny_file_report(
        inventory,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold,
        safe_paths=args.safe_paths,
    )

    output = json.dumps(report, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
