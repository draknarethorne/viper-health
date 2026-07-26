"""CLI for capturing and diffing churn snapshots (spec Section 11)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from viper_health.analyzers.churn import compute_churn
from viper_health.collectors.snapshot import (
    capture_snapshot,
    load_snapshot,
    save_snapshot,
)
from viper_health.collectors.target_roots import (
    ALL_CATEGORIES,
    get_all_targets,
    get_targets_for_category,
)
from viper_health.utils.fs_counter import format_bytes

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


def _cmd_capture(args: argparse.Namespace) -> int:
    if args.category == "all":
        roots = get_all_targets()
    elif args.category in ALL_CATEGORIES:
        roots = get_targets_for_category(args.category)
    else:
        print(f"{Fore.RED}❌ Unknown category: {args.category}{Style.RESET_ALL}",
              file=sys.stderr)
        return 2

    print(f"{Fore.CYAN}{Style.BRIGHT}📸 Capturing snapshot "
          f"({len(roots)} roots)...{Style.RESET_ALL}")

    snapshot = capture_snapshot(roots)
    save_snapshot(snapshot, args.output)

    print(f"{Fore.GREEN}✅ Snapshot saved: {args.output}{Style.RESET_ALL}")
    print(f"   Timestamp: {snapshot.timestamp_utc}")
    print(f"   Entries:   {len(snapshot.entries)}")
    total_files = sum(e.file_count for e in snapshot.entries)
    print(f"   Files:     {total_files:,}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    try:
        previous = load_snapshot(args.previous)
        current = load_snapshot(args.current)
    except (FileNotFoundError, ValueError) as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1

    report = compute_churn(previous, current)
    color = _severity_color(report.overall_severity)

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}📈 CHURN ANALYSIS{Style.RESET_ALL}")
    print("=" * 70)
    print(f"Previous: {report.previous_timestamp}")
    print(f"Current:  {report.current_timestamp}")
    print(f"Elapsed:  {report.elapsed_days:.2f} days")
    print()

    active = [f for f in report.findings if f.files_delta != 0]
    if not active:
        print(f"{Fore.GREEN}No churn detected between snapshots.{Style.RESET_ALL}")
    else:
        for f in active:
            fcolor = _severity_color(f.severity)
            sign = "+" if f.files_delta >= 0 else ""
            print(f"{fcolor}• {f.name}{Style.RESET_ALL}  [{f.risk_label}]")
            print(f"   {f.path}")
            print(
                f"   Δ files: {sign}{f.files_delta:,}  |  "
                f"Δ size: {sign}{format_bytes(f.bytes_delta)}"
            )
            print(
                f"   Velocity: {fcolor}{f.files_per_day:,.0f} files/day"
                f"{Style.RESET_ALL} ({format_bytes(f.bytes_per_day)}/day)"
            )
            print()

    print(
        f"{Style.BRIGHT}Overall Churn: {color}"
        f"{report.overall_severity.upper()}{Style.RESET_ALL} "
        f"({report.critical_count} critical, {report.warning_count} warning)"
    )
    print("=" * 70)

    return 1 if report.overall_severity == "critical" else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for snapshot capture/diff."""
    parser = argparse.ArgumentParser(
        description="Viper Health Snapshot & Churn Tracking (spec Section 11)",
        epilog="""
Examples:
  # Capture a baseline snapshot of all target roots
  python -m viper_health.cli.scan_snapshot capture --output data/snapshots/day1.json

  # Capture just cloud-sync roots
  python -m viper_health.cli.scan_snapshot capture --category cloud_sync --output cloud1.json

  # Compare two snapshots to compute churn velocity
  python -m viper_health.cli.scan_snapshot diff --previous data/snapshots/day1.json --current data/snapshots/day2.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="Capture a snapshot")
    cap.add_argument("--category", default="all",
                     help="Category or 'all' (default: all)")
    cap.add_argument("--output", type=Path, required=True,
                     help="Output snapshot JSON path")
    cap.set_defaults(func=_cmd_capture)

    dif = sub.add_parser("diff", help="Diff two snapshots for churn")
    dif.add_argument("--previous", type=Path, required=True, help="Earlier snapshot")
    dif.add_argument("--current", type=Path, required=True, help="Later snapshot")
    dif.set_defaults(func=_cmd_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
