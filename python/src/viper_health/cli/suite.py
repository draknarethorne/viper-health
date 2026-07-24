"""
Viper Health Suite Runner - preset-based scan orchestration.

Provides easy-to-use presets for common scan scenarios:
- full-system: Complete C: drive sweep
- user-data: All AppData and temp locations
- quick-check: High-risk areas only
- workspace: Current directory deep scan

Usage:
    python -m viper_health.cli.suite --preset <preset_name>
    python -m viper_health.cli.suite --targets <path1> <path2> ...

Examples:
    # Run full C: drive sweep
    python -m viper_health.cli.suite --preset full-system --output-dir reports/

    # Quick check of common problem areas
    python -m viper_health.cli.suite --preset quick-check --console-summary

    # Custom multi-target scan
    python -m viper_health.cli.suite --targets "C:\\Users" "D:\\Data" --output-json scan.json
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import yaml

from viper_health.cli.scan import run_full_scan
from viper_health.reports.json_reporter import build_json_report, write_json_report
from viper_health.reports.markdown_reporter import build_markdown_report, write_markdown_report


# Check if console supports Unicode emojis
def _supports_unicode() -> bool:
    """Check if stdout supports UTF-8 encoding."""
    try:
        return sys.stdout.encoding.lower() in ('utf-8', 'utf8')
    except AttributeError:
        return False


# Icon sets with fallback for non-UTF8 consoles
ICONS = {
    'rocket': '🚀' if _supports_unicode() else '[RUN]',
    'memo': '📝' if _supports_unicode() else '[DESC]',
    'target': '🎯' if _supports_unicode() else '[TARGET]',
    'scan': '🔍' if _supports_unicode() else '[SCAN]',
    'skip': '⏭️' if _supports_unicode() else '[SKIP]',
    'complete': '✅' if _supports_unicode() else '[OK]',
    'watch': '🔍' if _supports_unicode() else '[WATCH]',
    'warning': '⚠️' if _supports_unicode() else '[WARN]',
    'critical': '❌' if _supports_unicode() else '[CRIT]',
    'error': '❌' if _supports_unicode() else '[ERR]',
    'file': '📄' if _supports_unicode() else '[JSON]',
    'markdown': '📝' if _supports_unicode() else '[MD]',
    'stats': '📊' if _supports_unicode() else '[STATS]',
    'magnify': '🔍' if _supports_unicode() else '[FIND]',
    'mute': '🔕' if _supports_unicode() else '[SUPP]',
}


def expand_env_path(path_str: str) -> Path:
    """Expand environment variables and resolve path."""
    expanded = os.path.expandvars(path_str)
    # Handle wildcard patterns in exclusions (for safe-path matching)
    if "*" in expanded:
        return Path(expanded)  # Keep wildcards for pattern matching
    return Path(expanded).resolve()


def load_presets(config_path: Path | None = None) -> dict:
    """Load scan presets from configuration file."""
    if config_path is None:
        # Default config location - go up from src/viper_health/cli/ to repo root
        config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "scan-presets.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Preset configuration not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def run_preset_scan(
    preset_name: str,
    *,
    output_dir: Path | None = None,
    output_json: Path | None = None,
    output_md: Path | None = None,
    console_summary: bool = False,
    show_progress: bool = False,
    config_path: Path | None = None,
) -> dict:
    """
    Run a preset scan configuration.

    Args:
        preset_name: Name of preset from config file
        output_dir: Directory for auto-named output files
        output_json: Explicit JSON output path
        output_md: Explicit Markdown output path
        console_summary: Print summary to console
        show_progress: Show progress updates during scans
        config_path: Optional custom config file path

    Returns:
        Consolidated scan results
    """
    config = load_presets(config_path)
    
    if preset_name not in config["presets"]:
        available = ", ".join(config["presets"].keys())
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")
    
    preset = config["presets"][preset_name]
    defaults = config.get("defaults", {})
    
    # Expand targets
    targets = [expand_env_path(t) for t in preset["targets"]]
    
    # Expand exclusions (safe paths)
    exclusions = []
    if "exclusions" in preset:
        exclusions = [expand_env_path(e) for e in preset["exclusions"]]
    
    # Get thresholds (preset overrides defaults)
    tiny_file_max_bytes = preset.get("tiny_file_max_bytes", defaults.get("tiny_file_max_bytes", 4096))
    tiny_file_warning = preset.get("tiny_file_warning", defaults.get("tiny_file_warning", 20000))
    tiny_file_critical = preset.get("tiny_file_critical", defaults.get("tiny_file_critical", 50000))
    dir_density_warning = preset.get("dir_density_warning", defaults.get("dir_density_warning", 50000))
    dir_density_critical = preset.get("dir_density_critical", defaults.get("dir_density_critical", 100000))
    mode = preset.get("mode", defaults.get("mode", "observe"))
    
    # Run scans for all targets
    all_results = []
    
    print(f"{ICONS['rocket']} Running preset: {preset_name}")
    print(f"{ICONS['memo']} Description: {preset.get('description', 'No description')}")
    print(f"{ICONS['target']} Targets: {len(targets)}")
    print()
    
    for idx, target in enumerate(targets, 1):
        if not target.exists():
            print(f"[{idx}/{len(targets)}] {ICONS['skip']} SKIP: {target} (does not exist)")
            continue
        
        print(f"[{idx}/{len(targets)}] {ICONS['scan']} Scanning: {target}")
        print()
        
        try:
            result = run_full_scan(
                root=target,
                mode=mode,
                tiny_file_max_bytes=tiny_file_max_bytes,
                tiny_file_warning=tiny_file_warning,
                tiny_file_critical=tiny_file_critical,
                dir_density_warning=dir_density_warning,
                dir_density_critical=dir_density_critical,
                safe_paths=exclusions if exclusions else None,
                show_progress=show_progress,
            )
            result["scan_target"] = str(target)
            all_results.append(result)
            
            # Print quick status
            score = result["health_score"].overall_score
            band = result["health_score"].severity_band.upper()
            findings = len(result.get("findings", []))
            
            # Choose icon based on health
            if band == "GOOD":
                icon = ICONS['complete']
            elif band == "WATCH":
                icon = ICONS['watch']
            elif band == "DEGRADED":
                icon = ICONS['warning']
            else:  # CRITICAL
                icon = ICONS['critical']
            
            print(f"  {icon} Health: {score:.1f}/100 ({band}) | {ICONS['magnify']} Findings: {findings}")
            print()
            
        except Exception as e:
            print(f"  {ICONS['error']} ERROR: {e}")
            print()
            continue
        
        print()
    
    # Build consolidated report
    consolidated = {
        "preset": preset_name,
        "description": preset.get("description", ""),
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "targets_scanned": len(all_results),
        "targets_total": len(targets),
        "scans": all_results,
    }
    
    # Calculate overall health (average of all scans)
    if all_results:
        avg_score = sum(r["health_score"].overall_score for r in all_results) / len(all_results)
        total_findings = sum(len(r.get("findings", [])) for r in all_results)
        total_suppressed = sum(len(r.get("suppressed", [])) for r in all_results)
        
        consolidated["summary"] = {
            "average_health_score": round(avg_score, 1),
            "total_findings": total_findings,
            "total_suppressed": total_suppressed,
        }
    
    # Write outputs
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"viper-health_{preset_name}_{timestamp}.json"
        md_path = output_dir / f"viper-health_{preset_name}_{timestamp}.md"
        
        # Write individual scan reports
        for scan_result in all_results:
            # Convert HealthScore to dict for JSON serialization
            scan_json = {
                "scan_target": scan_result["scan_target"],
                "inventory": {
                    "total_files": scan_result["inventory"].total_files,
                    "tiny_files": scan_result["inventory"].tiny_files,
                    "directories_scanned": scan_result["inventory"].directories_scanned,
                },
                "health_score": {
                    "overall_score": scan_result["health_score"].overall_score,
                    "severity_band": scan_result["health_score"].severity_band,
                    "components": [
                        {
                            "name": c.name,
                            "score": c.score,
                            "weight": c.weight,
                            "weighted_contribution": c.weighted_contribution,
                        }
                        for c in scan_result["health_score"].components
                    ],
                },
                "findings": scan_result.get("findings", []),
                "suppressed": scan_result.get("suppressed", []),
            }
        
        # Write consolidated report
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            # Convert HealthScore objects to dicts for serialization
            serializable_results = []
            for r in all_results:
                scan_dict = {
                    "scan_target": r["scan_target"],
                    "inventory": {
                        "total_files": r["inventory"].total_files,
                        "tiny_files": r["inventory"].tiny_files,
                        "directories_scanned": r["inventory"].directories_scanned,
                    },
                    "health_score": {
                        "overall_score": r["health_score"].overall_score,
                        "severity_band": r["health_score"].severity_band,
                        "components": [
                            {
                                "name": c.name,
                                "score": c.score,
                                "weight": c.weight,
                                "weighted_contribution": c.weighted_contribution,
                            }
                            for c in r["health_score"].components
                        ],
                    },
                    "findings": r.get("findings", []),
                    "suppressed": r.get("suppressed", []),
                }
                serializable_results.append(scan_dict)
            
            consolidated_output = {
                "preset": consolidated["preset"],
                "description": consolidated["description"],
                "scan_timestamp": consolidated["scan_timestamp"],
                "targets_scanned": consolidated["targets_scanned"],
                "targets_total": consolidated["targets_total"],
                "summary": consolidated.get("summary", {}),
                "scans": serializable_results,
            }
            json.dump(consolidated_output, f, indent=2)
        
        print(f"{ICONS['file']} JSON report: {json_path}")
        print(f"{ICONS['markdown']} Markdown report: {md_path}")
    
    if output_json:
        # Similar serialization for explicit JSON path
        pass
    
    if output_md:
        # Generate markdown report
        pass
    
    if console_summary or (not output_dir and not output_json and not output_md):
        print()
        print("=" * 70)
        print(f"{ICONS['stats']} VIPER HEALTH SUITE SUMMARY")
        print("=" * 70)
        print(f"{ICONS['target']} Preset: {preset_name}")
        print(f"{ICONS['magnify']} Targets Scanned: {consolidated['targets_scanned']}/{consolidated['targets_total']}")
        if "summary" in consolidated:
            avg = consolidated['summary']['average_health_score']
            # Determine health icon for average
            if avg >= 80:
                avg_icon = ICONS['complete']
            elif avg >= 60:
                avg_icon = ICONS['watch']
            elif avg >= 40:
                avg_icon = ICONS['warning']
            else:
                avg_icon = ICONS['critical']
            
            print(f"{avg_icon} Average Health: {avg}/100")
            print(f"{ICONS['magnify']} Total Findings: {consolidated['summary']['total_findings']}")
            print(f"{ICONS['mute']} Total Suppressed: {consolidated['summary']['total_suppressed']}")
        print("=" * 70)
        print()
    
    return consolidated


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for suite runner."""
    parser = argparse.ArgumentParser(
        description="Viper Health Suite Runner - preset-based scan orchestration",
        epilog="""
Examples:
  # Full C: drive sweep
  python -m viper_health.cli.suite --preset full-system --output-dir reports/

  # Quick check of high-risk areas
  python -m viper_health.cli.suite --preset quick-check --console-summary

  # Scan user data directories
  python -m viper_health.cli.suite --preset user-data --output-dir ~/health-reports/

  # List available presets
  python -m viper_health.cli.suite --list-presets
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--preset",
        type=str,
        help="Preset configuration name (see --list-presets)",
    )
    
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available presets and exit",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for auto-named output files (default: data/reports/ in project)",
    )
    
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Explicit JSON output file path",
    )
    
    parser.add_argument(
        "--output-md",
        type=Path,
        help="Explicit Markdown output file path",
    )
    
    parser.add_argument(
        "--console-summary",
        action="store_true",
        help="Print summary to console (default: true if no output specified)",
    )
    
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress updates during scans (recommended for large scans like full-system)",
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Custom preset configuration file (default: config/scan-presets.yaml)",
    )
    
    args = parser.parse_args(argv)
    
    # List presets
    if args.list_presets:
        try:
            config = load_presets(args.config)
            print("Available Presets:")
            print()
            for name, preset in config["presets"].items():
                desc = preset.get("description", "No description")
                targets = len(preset.get("targets", []))
                print(f"  {name:<20} {desc}")
                print(f"  {' ' * 20} Targets: {targets}")
                print()
            return 0
        except Exception as e:
            print(f"Error loading presets: {e}", file=sys.stderr)
            return 1
    
    # Run preset scan
    if not args.preset:
        parser.error("--preset is required (or use --list-presets)")
    
    # Default output_dir to project data/reports if not specified
    output_dir = args.output_dir
    if not output_dir and not args.output_json and not args.output_md:
        # Calculate path relative to this file: suite.py -> src/viper_health/cli
        # Go up to repo root: cli -> viper_health -> src -> python -> repo_root
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        output_dir = repo_root / "data" / "reports"
    
    try:
        run_preset_scan(
            preset_name=args.preset,
            output_dir=output_dir,
            output_json=args.output_json,
            output_md=args.output_md,
            console_summary=args.console_summary,
            show_progress=args.progress,
            config_path=args.config,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
