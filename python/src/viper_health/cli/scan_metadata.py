"""CLI for composite metadata pressure analysis (spec 4.3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.analyzers.metadata_pressure import analyze_metadata_pressure
from viper_health.collectors.file_inventory import scan_file_inventory

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def _severity_color(severity: str) -> str:
    return {
        "good": Fore.GREEN,
        "warning": Fore.YELLOW,
        "critical": Fore.RED,
    }.get(severity, Fore.CYAN)


def _severity_icon(severity: str) -> str:
    return {"good": "✅", "warning": "⚠️", "critical": "❌"}.get(severity, "•")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for composite metadata pressure analysis."""
    parser = argparse.ArgumentParser(
        description="Viper Health Metadata Pressure Composite (spec 4.3)",
        epilog="""
Examples:
  # Analyze a directory tree's metadata pressure
  python -m viper_health.cli.scan_metadata --root C:\\Users\\me\\AppData

  # Include MFT signals (requires admin)
  python -m viper_health.cli.scan_metadata --root C:\\ --drive C:

  # Save results
  python -m viper_health.cli.scan_metadata --root . --output metadata.json

Combines tiny-file totals, directory counts, and (optionally) MFT size/
fragmentation into a single composite pressure score.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", type=str, default=".", help="Directory to analyze")
    parser.add_argument(
        "--drive",
        type=str,
        default=None,
        help="Optional drive for MFT signals (e.g., C:) - requires admin",
    )
    parser.add_argument("--output", type=Path, help="Save results to JSON file")

    args = parser.parse_args(argv)

    print(
        f"{Fore.CYAN}{Style.BRIGHT}🔍 Scanning metadata pressure: "
        f"{args.root}{Style.RESET_ALL}\n"
    )

    try:
        inventory = scan_file_inventory(args.root)
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1

    mft_size_bytes = None
    mft_fragments = None
    if args.drive:
        try:
            from viper_health.collectors.mft_info import get_mft_info

            mft = get_mft_info(args.drive)
            mft_size_bytes = mft.mft_size_bytes
            mft_fragments = mft.mft_fragments
        except Exception as e:  # noqa: BLE001 - MFT is optional/best-effort
            print(
                f"{Fore.YELLOW}⚠️  Skipping MFT signals: {e}{Style.RESET_ALL}\n"
            )

    report = analyze_metadata_pressure(
        tiny_files_total=inventory.tiny_files,
        directories_total=inventory.directories_scanned,
        mft_size_bytes=mft_size_bytes,
        mft_fragments=mft_fragments,
    )

    color = _severity_color(report.overall_severity)

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}🧮 METADATA PRESSURE COMPOSITE{Style.RESET_ALL}")
    print("=" * 70)
    print(f"Scope: {args.root}")
    print(f"Total files scanned: {inventory.total_files:,}")
    print()

    for s in report.signals:
        icon = _severity_icon(s.severity)
        scolor = _severity_color(s.severity)
        print(f"  {scolor}{icon} {s.name}{Style.RESET_ALL}")
        print(
            f"      value={s.value:,}  "
            f"warn>={s.warning_threshold:,}  crit>={s.critical_threshold:,}"
        )

    print()
    print(
        f"{Style.BRIGHT}Pressure Score: {color}{report.pressure_score}/100"
        f"{Style.RESET_ALL} (higher = more pressure)"
    )
    print(
        f"{Style.BRIGHT}Overall: {color}{report.overall_severity.upper()}"
        f"{Style.RESET_ALL} "
        f"({report.critical_count} critical, {report.warning_count} warning)"
    )
    print("=" * 70 + "\n")

    if report.overall_severity == "critical":
        print(
            f"{Fore.RED}{Style.BRIGHT}🚨 High metadata pressure.{Style.RESET_ALL}\n"
            "   • Identify tiny-file hotspots: python -m viper_health.cli.scan_tiny_files\n"
            "   • Check MFT health (admin): python -m viper_health.cli.scan_mft\n"
            "   • Reduce small-file churn (caches, node_modules, package stores)"
        )
    elif report.overall_severity == "warning":
        print(
            f"{Fore.YELLOW}💡 Moderate pressure — worth watching.{Style.RESET_ALL}\n"
            "   • Track over time with snapshots (scan_snapshot)\n"
            "   • Archive stale small-file trees where possible"
        )
    else:
        print(f"{Fore.GREEN}✅ Metadata pressure is within normal bounds.{Style.RESET_ALL}")

    if args.output:
        payload = {
            "scope": str(args.root),
            "total_files": inventory.total_files,
            "pressure_score": report.pressure_score,
            "overall_severity": report.overall_severity,
            "signals": [
                {
                    "name": s.name,
                    "value": s.value,
                    "warning_threshold": s.warning_threshold,
                    "critical_threshold": s.critical_threshold,
                    "severity": s.severity,
                }
                for s in report.signals
            ],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\n{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")

    return 1 if report.overall_severity == "critical" else 0


if __name__ == "__main__":
    sys.exit(main())
