"""CLI for churn/cache/residue category pressure scans (spec 4.4-4.7)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.analyzers.category_pressure import CategoryReport, analyze_category
from viper_health.collectors.target_roots import (
    ALL_CATEGORIES,
    CATEGORY_BROWSER_CACHE,
    CATEGORY_CLOUD_SYNC,
    CATEGORY_TELEMETRY_LOG,
    CATEGORY_UPDATE_RESIDUE,
    get_targets_for_category,
)
from viper_health.utils.fs_counter import format_bytes

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = MAGENTA = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


_CATEGORY_LABELS = {
    CATEGORY_CLOUD_SYNC: "☁️  Cloud-Sync Churn (4.4)",
    CATEGORY_BROWSER_CACHE: "🌐 Browser/WebView Cache (4.5)",
    CATEGORY_UPDATE_RESIDUE: "📦 Update/Installer Residue (4.6)",
    CATEGORY_TELEMETRY_LOG: "📊 Telemetry/Log Churn (4.7)",
}

_CATEGORY_ALIASES = {
    "cloud": CATEGORY_CLOUD_SYNC,
    "cloud-sync": CATEGORY_CLOUD_SYNC,
    "browser": CATEGORY_BROWSER_CACHE,
    "cache": CATEGORY_BROWSER_CACHE,
    "update": CATEGORY_UPDATE_RESIDUE,
    "updates": CATEGORY_UPDATE_RESIDUE,
    "residue": CATEGORY_UPDATE_RESIDUE,
    "telemetry": CATEGORY_TELEMETRY_LOG,
    "logs": CATEGORY_TELEMETRY_LOG,
}


def _severity_color(severity: str) -> str:
    return {
        "good": Fore.GREEN,
        "warning": Fore.YELLOW,
        "critical": Fore.RED,
    }.get(severity, Fore.CYAN)


def _severity_icon(severity: str) -> str:
    return {"good": "✅", "warning": "⚠️", "critical": "❌"}.get(severity, "•")


def _print_category(report: CategoryReport) -> None:
    label = _CATEGORY_LABELS.get(report.category, report.category)
    color = _severity_color(report.overall_severity)

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}{label}{Style.RESET_ALL}")
    print("=" * 70)

    if not report.findings:
        print(f"{Fore.GREEN}No target roots found on this system.{Style.RESET_ALL}\n")
        return

    for f in report.findings:
        icon = _severity_icon(f.severity)
        fcolor = _severity_color(f.severity)
        print(f"{fcolor}{icon} {f.name}{Style.RESET_ALL}")
        print(f"   Path: {f.path}")
        print(
            f"   Files: {f.file_count:,}  |  "
            f"Size: {format_bytes(f.total_bytes)}  |  "
            f"Tiny: {f.tiny_files:,}"
        )
        print(f"   {fcolor}{f.severity.upper()}{Style.RESET_ALL}: {f.reason}")
        print()

    print(
        f"{Style.BRIGHT}Category Totals:{Style.RESET_ALL} "
        f"{report.total_files:,} files, "
        f"{format_bytes(report.total_bytes)}, "
        f"{report.total_tiny_files:,} tiny files"
    )
    print(
        f"{Style.BRIGHT}Overall:{Style.RESET_ALL} "
        f"{color}{report.overall_severity.upper()}{Style.RESET_ALL} "
        f"({report.critical_count} critical, {report.warning_count} warning, "
        f"{report.good_count} good)"
    )
    print("=" * 70 + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for category pressure scans."""
    parser = argparse.ArgumentParser(
        description="Viper Health Churn/Cache/Residue Scanner (spec 4.4-4.7)",
        epilog="""
Examples:
  # Scan all categories
  python -m viper_health.cli.scan_targets --category all

  # Scan just browser/webview caches
  python -m viper_health.cli.scan_targets --category browser

  # Scan cloud-sync roots and save JSON
  python -m viper_health.cli.scan_targets --category cloud --output cloud.json

Categories: cloud, browser, update, telemetry, all
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--category",
        type=str,
        default="all",
        help="Category to scan: cloud, browser, update, telemetry, all (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )

    args = parser.parse_args(argv)

    requested = args.category.strip().lower()
    if requested == "all":
        categories = list(ALL_CATEGORIES)
    elif requested in _CATEGORY_ALIASES:
        categories = [_CATEGORY_ALIASES[requested]]
    elif requested in ALL_CATEGORIES:
        categories = [requested]
    else:
        print(
            f"{Fore.RED}❌ Unknown category: {args.category}{Style.RESET_ALL}",
            file=sys.stderr,
        )
        print("Valid: cloud, browser, update, telemetry, all", file=sys.stderr)
        return 2

    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Scanning target categories...{Style.RESET_ALL}\n")

    reports: list[CategoryReport] = []
    for category in categories:
        roots = get_targets_for_category(category)
        report = analyze_category(category, roots)
        reports.append(report)
        _print_category(report)

    # Aggregate summary
    worst = "good"
    for r in reports:
        if r.overall_severity == "critical":
            worst = "critical"
            break
        if r.overall_severity == "warning":
            worst = "warning"

    color = _severity_color(worst)
    print(
        f"{Style.BRIGHT}Aggregate Health: {color}{worst.upper()}{Style.RESET_ALL}"
    )

    if worst == "good":
        print(f"{Fore.GREEN}✅ No churn/cache pressure detected.{Style.RESET_ALL}")
    else:
        print(
            f"{Fore.YELLOW}💡 Review flagged roots above. These are cleanup "
            f"candidates, but viper-health is read-only — clean manually and "
            f"observe a 60-min calm phase afterward.{Style.RESET_ALL}"
        )

    if args.output:
        payload = {
            "categories": [
                {
                    "category": r.category,
                    "overall_severity": r.overall_severity,
                    "total_files": r.total_files,
                    "total_bytes": r.total_bytes,
                    "total_tiny_files": r.total_tiny_files,
                    "findings": [
                        {
                            "name": f.name,
                            "path": f.path,
                            "file_count": f.file_count,
                            "total_bytes": f.total_bytes,
                            "tiny_files": f.tiny_files,
                            "severity": f.severity,
                            "reason": f.reason,
                        }
                        for f in r.findings
                    ],
                }
                for r in reports
            ],
            "aggregate_severity": worst,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\n{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")

    return 1 if worst == "critical" else 0


if __name__ == "__main__":
    sys.exit(main())
