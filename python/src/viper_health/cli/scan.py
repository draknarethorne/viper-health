"""
Unified CLI entrypoint for viper-health.

Orchestrates full scan workflow:
- File inventory collection
- Multiple detector analysis (tiny-file hotspots, directory density)
- Health score calculation
- Multi-format reporting (JSON, Markdown, console)

Usage:
    python -m viper_health.cli.scan <root_path> [options]

Example:
    python -m viper_health.cli.scan C:/Users/scott/AppData --output-json report.json --output-md report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from viper_health.analyzers.directory_density import analyze_directory_density
from viper_health.analyzers.tiny_file_hotspots import analyze_tiny_file_hotspots
from viper_health.collectors.file_inventory import scan_file_inventory
from viper_health.reports.json_reporter import format_json_string, write_json_report
from viper_health.reports.markdown_reporter import write_markdown_report
from viper_health.reports.json_reporter import build_json_report
from viper_health.reports.markdown_reporter import build_markdown_report
from viper_health.scoring.health_score import (
    calculate_component_score,
    calculate_health_score,
)
from viper_health.utils.progress import ProgressReporter

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback no-op classes
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


# Check if console supports Unicode emojis
def _supports_unicode() -> bool:
    """Check if stdout supports UTF-8 encoding."""
    try:
        return sys.stdout.encoding.lower() in ('utf-8', 'utf8')
    except AttributeError:
        return False


# Icon sets with fallback for non-UTF8 consoles
ICONS = {
    'scan': '🔍' if _supports_unicode() else '[SCAN]',
    'complete': '✅' if _supports_unicode() else '[OK]',
    'warning': '⚠️' if _supports_unicode() else '[WARN]',
    'critical': '❌' if _supports_unicode() else '[CRIT]',
    'stats': '📊' if _supports_unicode() else '[STATS]',
    'folder': '📂' if _supports_unicode() else '[DIR]',
    'dir': '📁' if _supports_unicode() else '[DIRS]',
    'file': '📄' if _supports_unicode() else '[FILES]',
    'microscope': '🔬' if _supports_unicode() else '[TINY]',
    'magnify': '🔍' if _supports_unicode() else '[FIND]',
    'mute': '🔕' if _supports_unicode() else '[SUPP]',
    'bulb': '💡' if _supports_unicode() else '[TIP]',
    'bullet': '•' if _supports_unicode() else '-',
}


def run_full_scan(
    root: Path,
    *,
    mode: str = "observe",
    tiny_file_max_bytes: int = 4096,
    tiny_file_warning: int = 20_000,
    tiny_file_critical: int = 50_000,
    dir_density_warning: int = 50_000,
    dir_density_critical: int = 100_000,
    safe_paths: list[Path] | None = None,
    exclude_paths: list[Path | str] | None = None,
    show_progress: bool = False,
) -> dict:
    """
    Execute full viper-health scan workflow.

    Args:
        root: Root directory to scan
        mode: Execution mode (observe/maintenance)
        tiny_file_max_bytes: Threshold for tiny-file classification
        tiny_file_warning: Warning threshold for tiny-file hotspots
        tiny_file_critical: Critical threshold for tiny-file hotspots
        dir_density_warning: Warning threshold for directory density
        dir_density_critical: Critical threshold for directory density
        safe_paths: Optional list of paths to suppress from findings
        exclude_paths: Optional paths/globs to prune from the walk entirely
        show_progress: Show progress updates during scan

    Returns:
        Complete scan results dictionary
    """
    # Step 1: Collect inventory with progress reporting
    progress = ProgressReporter(enabled=show_progress, root_path=root)
    progress.start(f"Scanning {root}...")
    
    inventory = scan_file_inventory(
        root,
        tiny_file_max_bytes=tiny_file_max_bytes,
        progress_callback=progress.update if show_progress else None,
        progress_interval=100,
        exclude_paths=exclude_paths,
    )
    
    progress.finish(inventory.directories_scanned, inventory.total_files)

    # Step 2: Run detectors
    tiny_hotspots = analyze_tiny_file_hotspots(
        inventory=inventory,
        warning_threshold=tiny_file_warning,
        critical_threshold=tiny_file_critical,
        safe_paths=safe_paths,
    )

    dir_density = analyze_directory_density(
        inventory=inventory,
        warning_threshold=dir_density_warning,
        critical_threshold=dir_density_critical,
        safe_paths=safe_paths,
    )

    # Step 3: Calculate component scores
    tiny_score = calculate_component_score(
        finding_count=tiny_hotspots.critical_count + tiny_hotspots.warning_count,
        warning_threshold=1,
        critical_threshold=3,
    )

    density_score = calculate_component_score(
        finding_count=dir_density.critical_count + dir_density.warning_count,
        warning_threshold=1,
        critical_threshold=3,
    )

    # Step 4: Calculate overall health score
    health_score = calculate_health_score(
        component_scores={
            "tiny_file_pressure": tiny_score,
            "directory_density": density_score,
        },
        weights={
            "tiny_file_pressure": 20.0,
            "directory_density": 10.0,
        },
    )

    # Step 5: Build findings list
    findings = []
    for hotspot in tiny_hotspots.findings:
        findings.append({
            "detector": "tiny_file_hotspots",
            "severity": hotspot.severity,
            "path": str(hotspot.path),
            "tiny_files": hotspot.tiny_files,
        })
    for finding in dir_density.findings:
        findings.append({
            "detector": "directory_density",
            "severity": finding.severity,
            "path": str(finding.path),
            "total_files": finding.total_files,
        })

    # Step 6: Build suppressed list
    suppressed = []
    for hotspot in tiny_hotspots.suppressed:
        suppressed.append({
            "detector": "tiny_file_hotspots",
            "severity": hotspot.severity,
            "path": str(hotspot.path),
            "tiny_files": hotspot.tiny_files,
        })
    for finding in dir_density.suppressed:
        suppressed.append({
            "detector": "directory_density",
            "severity": finding.severity,
            "path": str(finding.path),
            "total_files": finding.total_files,
        })

    # Step 7: Generate recommendations
    recommendations = []
    if health_score.severity_band == "critical":
        recommendations.append("CRITICAL: Immediate cleanup recommended to prevent performance degradation")
    elif health_score.severity_band == "degraded":
        recommendations.append("System health is degraded - schedule maintenance review")
    elif health_score.severity_band == "watch":
        recommendations.append("Monitor trends - approaching attention thresholds")

    if tiny_hotspots.critical_count > 0:
        recommendations.append(f"Review {tiny_hotspots.critical_count} critical tiny-file hotspot(s)")
    if dir_density.critical_count > 0:
        recommendations.append(f"Review {dir_density.critical_count} critical directory density finding(s)")

    return {
        "mode": mode,
        "scan_root": root,
        "inventory": inventory,
        "findings": findings,
        "suppressed": suppressed,
        "health_score": health_score,
        "recommendations": recommendations,
    }


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Viper Health unified scan - comprehensive SSD/filesystem diagnostics",
        epilog="""
Examples:
  # Scan AppData with console summary
  python -m viper_health.cli.scan C:/Users/scott/AppData/Local --console-summary

  # Full scan with JSON and Markdown reports
  python -m viper_health.cli.scan C:/Users/scott --output-json report.json --output-md report.md

  # Scan with custom thresholds and safe-path exclusions
  python -m viper_health.cli.scan C:/Temp --safe-path "C:/Temp/System" --console-summary

  # Use --help-full for detailed parameter descriptions
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Root directory to scan",
    )
    parser.add_argument(
        "--mode",
        choices=["observe", "maintenance"],
        default="observe",
        help="Execution mode (default: observe)",
    )
    parser.add_argument(
        "--tiny-max-bytes",
        type=int,
        default=4096,
        dest="tiny_max_bytes",
        help="Threshold for tiny-file classification in bytes (default: 4096)",
    )
    parser.add_argument(
        "--tiny-warning",
        type=int,
        default=20_000,
        help="Warning threshold for tiny-file hotspots (default: 20000)",
    )
    parser.add_argument(
        "--tiny-critical",
        type=int,
        default=50_000,
        help="Critical threshold for tiny-file hotspots (default: 50000)",
    )
    parser.add_argument(
        "--density-warning",
        type=int,
        default=50_000,
        help="Warning threshold for directory density (default: 50000)",
    )
    parser.add_argument(
        "--density-critical",
        type=int,
        default=100_000,
        help="Critical threshold for directory density (default: 100000)",
    )
    parser.add_argument(
        "--safe-path",
        type=Path,
        action="append",
        dest="safe_paths",
        help="Path to suppress from findings (can be specified multiple times)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_paths",
        help="Path or glob to skip entirely during the walk (can be specified multiple times)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        help="Write Markdown report to file",
    )
    parser.add_argument(
        "--console-summary",
        action="store_true",
        help="Print console summary (default: true if no output files specified)",
    )
    
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress updates during scan (recommended for large scans)",
    )

    args = parser.parse_args(argv)

    # Validate root exists
    if not args.root.exists():
        print(f"Error: Root path does not exist: {args.root}", file=sys.stderr)
        return 1

    # Run scan
    results = run_full_scan(
        root=args.root,
        mode=args.mode,
        tiny_file_max_bytes=args.tiny_max_bytes,
        tiny_file_warning=args.tiny_warning,
        tiny_file_critical=args.tiny_critical,
        dir_density_warning=args.density_warning,
        dir_density_critical=args.density_critical,
        safe_paths=args.safe_paths,
        exclude_paths=args.exclude_paths,
        show_progress=args.progress,
    )

    # Build reports
    json_report = build_json_report(
        scan_root=results["scan_root"],
        mode=results["mode"],
        total_files=results["inventory"].total_files,
        tiny_files=results["inventory"].tiny_files,
        directories_scanned=results["inventory"].directories_scanned,
        findings=results["findings"],
        suppressed=results["suppressed"],
        health_score=results["health_score"],
        recommendations=results["recommendations"],
    )

    md_report = build_markdown_report(
        scan_root=results["scan_root"],
        mode=results["mode"],
        total_files=results["inventory"].total_files,
        tiny_files=results["inventory"].tiny_files,
        directories_scanned=results["inventory"].directories_scanned,
        findings=results["findings"],
        suppressed=results["suppressed"],
        health_score=results["health_score"],
        recommendations=results["recommendations"],
    )

    # Output
    if args.output_json:
        write_json_report(json_report, args.output_json)
        print(f"JSON report written to {args.output_json}")

    if args.output_md:
        write_markdown_report(md_report, args.output_md)
        print(f"Markdown report written to {args.output_md}")

    # Console summary (default if no files specified)
    if args.console_summary or (not args.output_json and not args.output_md):
        # Determine health icon and color
        severity = results['health_score'].severity_band
        if severity == "good":
            health_icon = ICONS['complete']
            health_color = Fore.GREEN
        elif severity == "watch":
            health_icon = ICONS['warning']
            health_color = Fore.YELLOW
        elif severity == "degraded":
            health_icon = ICONS['warning']
            health_color = Fore.YELLOW
        else:  # critical
            health_icon = ICONS['critical']
            health_color = Fore.RED
        
        print("\n" + "="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}{ICONS['stats']} VIPER HEALTH SCAN SUMMARY{Style.RESET_ALL}")
        print("="*70)
        print(f"{ICONS['folder']} Root: {results['scan_root']}")
        print(f"{ICONS['dir']} Directories Scanned: {results['inventory'].directories_scanned:,}")
        print(f"{ICONS['file']} Files Scanned: {results['inventory'].total_files:,}")
        print(f"{ICONS['microscope']} Tiny Files (<{args.tiny_max_bytes} bytes): {results['inventory'].tiny_files:,}")
        print(f"{health_color}{Style.BRIGHT}{health_icon} Health Score: {results['health_score'].overall_score:.1f} / 100 ({results['health_score'].severity_band.upper()}){Style.RESET_ALL}")
        print(f"{ICONS['magnify']} Findings: {len(results['findings'])} | {ICONS['mute']} Suppressed: {len(results['suppressed'])}")
        print("="*70 + "\n")

        if results["recommendations"]:
            print(f"{Fore.YELLOW}{ICONS['bulb']} Recommendations:{Style.RESET_ALL}")
            for rec in results["recommendations"]:
                print(f"  {ICONS['bullet']} {rec}")
            print()

    # Exit code: 1 if critical severity, 0 otherwise
    return 1 if results["health_score"].severity_band == "critical" else 0


if __name__ == "__main__":
    sys.exit(main())
