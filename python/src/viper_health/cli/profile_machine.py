"""
Machine profile CLI for cross-machine SSD/filesystem health comparison.

Captures a single, comparable "machine profile" JSON that fingerprints a
machine's storage health: drive/bus info, disk space, TRIM, filesystem
tiny-file pressure, health score, and (optionally) I/O benchmark results.

The profile is written per-machine (default ``data/profiles/<hostname>.json``)
so multiple machines can commit their own profile to git and compare against
each other with ``compare_baseline``:

    # On each machine (laptop, desktop):
    python -m viper_health.cli.profile_machine --benchmark
    git add data/profiles/<hostname>.json && git commit && git push

    # On any machine, after `git pull`:
    python -m viper_health.cli.compare_baseline \
        --baseline data/profiles/DESKTOP.json \
        --current  data/profiles/LAPTOP.json --verbose

This CLI is read-only (observe mode). The optional ``--benchmark`` flag writes
a small temporary file to measure I/O and always cleans it up.
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from viper_health.benchmarks.io_bench import (
    assess_benchmark_performance,
    run_io_benchmark,
)
from viper_health.cli.scan import run_full_scan
from viper_health.collectors.disk_space import analyze_disk_space

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except ImportError:  # pragma: no cover - color is cosmetic
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""

    class Style:
        BRIGHT = RESET_ALL = ""


SCHEMA_VERSION = 1


def _collect_machine_info() -> dict:
    """Gather stable identity/hardware facts for this machine."""
    try:
        import os as _os

        cpu_count = _os.cpu_count()
    except Exception:  # pragma: no cover - defensive
        cpu_count = None

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": cpu_count,
    }


def build_machine_profile(
    root: Path,
    *,
    drive: str = "C:",
    include_drives: bool = True,
    include_trim: bool = True,
    run_benchmark: bool = False,
    benchmark_size_mb: int = 100,
    exclude_paths: list[str] | None = None,
    show_progress: bool = False,
) -> dict:
    """Build a comparable machine-profile dictionary.

    Args:
        root: Filesystem root to scan for tiny-file pressure.
        drive: Drive letter to inspect for space/TRIM (default ``C:``).
        include_drives: Query drive/SMART health (PowerShell; may be slow).
        include_trim: Query TRIM status (fsutil; may need admin).
        run_benchmark: Run a small I/O benchmark and include results.
        benchmark_size_mb: Test-file size for the benchmark, in MB.
        exclude_paths: Paths/globs to prune from the filesystem walk.
        show_progress: Emit progress updates during the scan.

    Returns:
        A JSON-serializable profile dict. Heavy/privileged collectors degrade
        gracefully: unavailable sections are recorded but never raise.
    """
    profile: dict = {
        "schema_version": SCHEMA_VERSION,
        "profile_type": "machine_profile",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "machine": _collect_machine_info(),
        "scan_root": str(root),
        "drive": drive,
    }

    # --- Elevation (best-effort; drives/TRIM depend on it) ------------------
    try:
        from viper_health.collectors.smart_data import is_elevated

        profile["elevated"] = is_elevated()
    except Exception:  # pragma: no cover - defensive
        profile["elevated"] = None

    # --- Disk space ---------------------------------------------------------
    try:
        space = analyze_disk_space(drive)
        profile["disk_space"] = asdict(space)
        profile["free_percent"] = space.free_percent
    except Exception as exc:  # pragma: no cover - environment dependent
        profile["disk_space"] = {"available": False, "error": str(exc)}

    # --- Filesystem tiny-file pressure (health score) -----------------------
    scan = run_full_scan(
        root=root,
        mode="observe",
        exclude_paths=exclude_paths,
        show_progress=show_progress,
    )
    inventory = scan["inventory"]
    health = scan["health_score"]
    total_files = inventory.total_files
    tiny_files = inventory.tiny_files
    tiny_ratio = round((tiny_files / total_files * 100.0), 2) if total_files else 0.0

    profile["total_files"] = total_files
    profile["tiny_files"] = tiny_files
    profile["tiny_file_ratio"] = tiny_ratio
    profile["directories_scanned"] = inventory.directories_scanned
    profile["total_bytes"] = inventory.total_bytes
    profile["findings_count"] = len(scan["findings"])
    profile["health_score"] = {
        "overall_score": round(health.overall_score, 1),
        "severity_band": health.severity_band,
    }

    # --- Drive / SMART health ----------------------------------------------
    if include_drives:
        try:
            from viper_health.collectors.smart_data import get_drive_health

            drives = get_drive_health()
            profile["drives"] = [asdict(d) for d in drives]
        except Exception as exc:  # pragma: no cover - environment dependent
            profile["drives"] = {"available": False, "error": str(exc)}

    # --- TRIM ---------------------------------------------------------------
    if include_trim:
        try:
            from viper_health.collectors.trim_status import check_trim_status

            trim = check_trim_status(drive)
            profile["trim"] = asdict(trim)
        except Exception as exc:  # environment/permission dependent
            profile["trim"] = {"available": False, "error": str(exc)}

    # --- I/O benchmark (optional; writes a temp file) -----------------------
    if run_benchmark:
        try:
            results = run_io_benchmark(
                target_dir=root if root.is_dir() else None,
                test_file_size_mb=benchmark_size_mb,
            )
            profile["benchmark_results"] = [
                {
                    "test_name": r.test_name,
                    "operation": r.operation,
                    "pattern": r.pattern,
                    "throughput_mb_s": round(r.throughput_mb_s, 2),
                    "iops": round(r.iops, 0),
                    "severity": assess_benchmark_performance(r)["severity"],
                }
                for r in results
            ]
        except Exception as exc:  # pragma: no cover - environment dependent
            profile["benchmark_results"] = {"available": False, "error": str(exc)}

    return profile


def _default_output_path(hostname: str) -> Path:
    """Default profile path: ``data/profiles/<HOSTNAME>.json`` at repo root."""
    # profile_machine.py -> cli -> viper_health -> src -> python -> <repo root>
    repo_root = Path(__file__).resolve().parents[4]
    safe_host = "".join(c if c.isalnum() or c in "-_." else "_" for c in hostname)
    return repo_root / "data" / "profiles" / f"{safe_host}.json"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for capturing a machine profile."""
    parser = argparse.ArgumentParser(
        description="Capture a comparable machine profile for cross-machine "
        "SSD/filesystem health comparison.",
        epilog="""
Examples:
  # Capture this machine's profile (default: user home, no benchmark)
  python -m viper_health.cli.profile_machine

  # Include an I/O benchmark and scan a specific root
  python -m viper_health.cli.profile_machine C:/Users/scott --benchmark

  # Compare two machines after `git pull`
  python -m viper_health.cli.compare_baseline \\
      --baseline data/profiles/DESKTOP.json \\
      --current  data/profiles/LAPTOP.json --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "root",
        type=Path,
        nargs="?",
        default=Path.home(),
        help="Root directory to scan for tiny-file pressure (default: user home)",
    )
    parser.add_argument(
        "--drive",
        default="C:",
        help="Drive to inspect for space/TRIM (default: C:)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path (default: data/profiles/<hostname>.json)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run a small I/O benchmark and include results (writes a temp file)",
    )
    parser.add_argument(
        "--benchmark-size",
        type=int,
        default=100,
        help="Benchmark test-file size in MB (default: 100)",
    )
    parser.add_argument(
        "--no-drives",
        action="store_true",
        help="Skip drive/SMART health collection (faster, no PowerShell)",
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Skip TRIM status collection",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_paths",
        help="Path or glob to skip during the walk (repeatable)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress updates during the scan (recommended for large roots)",
    )

    args = parser.parse_args(argv)

    if not args.root.exists():
        print(f"Error: Root path does not exist: {args.root}", file=sys.stderr)
        return 1

    print(f"{Fore.CYAN}{Style.BRIGHT}🧭 Building machine profile...{Style.RESET_ALL}")
    print(f"   Root: {args.root}")
    if args.benchmark:
        print(f"   Benchmark: enabled ({args.benchmark_size} MB)")

    profile = build_machine_profile(
        root=args.root,
        drive=args.drive,
        include_drives=not args.no_drives,
        include_trim=not args.no_trim,
        run_benchmark=args.benchmark,
        benchmark_size_mb=args.benchmark_size,
        exclude_paths=args.exclude_paths,
        show_progress=args.progress,
    )

    output = args.output or _default_output_path(profile["machine"]["hostname"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    # --- Summary ------------------------------------------------------------
    hs = profile["health_score"]
    print("\n" + "=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}🧭 MACHINE PROFILE{Style.RESET_ALL}")
    print("=" * 70)
    print(f"  Machine:       {profile['machine']['hostname']} "
          f"({profile['machine']['os']} {profile['machine']['os_release']})")
    print(f"  Scan root:     {profile['scan_root']}")
    print(f"  Files:         {profile['total_files']:,}")
    print(f"  Tiny files:    {profile['tiny_files']:,} "
          f"({profile['tiny_file_ratio']:.2f}% of files)")
    print(f"  Directories:   {profile['directories_scanned']:,}")
    if "free_percent" in profile:
        print(f"  Free space:    {profile['free_percent']:.1f}%")
    print(f"  Health score:  {hs['overall_score']:.1f} / 100 "
          f"({hs['severity_band'].upper()})")
    if isinstance(profile.get("benchmark_results"), list):
        for b in profile["benchmark_results"]:
            print(f"    {b['test_name']:<18} {b['throughput_mb_s']:>8.1f} MB/s "
                  f"({b['severity'].upper()})")
    print("=" * 70)
    print(f"\n✅ Profile written to {output}")
    print("   Commit it so other machines can compare:")
    print(f"     git add {output.as_posix()}")
    print("     git commit -m \"profile: <machine> storage snapshot\" && git push")
    print("   Then on another machine after `git pull`:")
    print("     python -m viper_health.cli.compare_baseline \\")
    print(f"        --baseline <other-machine>.json --current {output.name} --verbose")

    return 0


if __name__ == "__main__":
    sys.exit(main())
