"""Reclaimable-space + background-load CLI (observe-first, optional safe clean).

By default this reports reclaimable space, startup/service load, and background
processes with advisory guidance — it modifies nothing.

``--clean`` enables the safety-gated cleanup engine, which:
- is **dry-run by default** (add ``--apply`` to act),
- only touches low-risk auto-cleanable temp/log/crash files under the approved
  allowlist and never under an immutable/system root,
- quarantines by default (``--delete`` for irreversible removal),
- honors file/byte caps and writes a JSON manifest.

High-risk items (recycle bin, browser/app caches, update caches, user data) are
never auto-cleaned; the report prints the safe manual step for each.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from viper_health.analyzers.startup_load import analyze_startup
from viper_health.collectors.reclaimable_space import scan_reclaimable_space
from viper_health.collectors.startup_items import collect_startup_inventory
from viper_health.utils.fs_counter import format_bytes
from viper_health.maintenance.safe_cleanup import (
    DELETE,
    QUARANTINE,
    execute_cleanup,
    plan_cleanup,
)

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except ImportError:  # pragma: no cover - cosmetic
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""

    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def _gib(value: int) -> str:
    return format_bytes(value)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_allowlist() -> tuple[list[str], list[str]]:
    path = _repo_root() / "config" / "allowlist.paths.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        data = {}
    immutable = [os.path.expandvars(p) for p in data.get("immutable_roots", [])]
    approved = [os.path.expandvars(p) for p in data.get("approved_cleanup_roots", [])]
    return approved, immutable


_SAFETY_ICON = {"safe": Fore.GREEN, "caution": Fore.YELLOW, "review": Fore.CYAN}


def _print_report(report, *, show_startup: bool) -> None:
    print("=" * 72)
    print(f"{Fore.CYAN}{Style.BRIGHT}RECLAIMABLE SPACE (observe-only){Style.RESET_ALL}")
    print("=" * 72)
    for target in report.targets:
        color = _SAFETY_ICON.get(target.safety_class, Fore.CYAN)
        auto = " [auto]" if target.auto_cleanable else ""
        admin = " (admin)" if target.requires_admin else ""
        print(f"  {color}{_gib(target.size_bytes):>10}{Style.RESET_ALL}  "
              f"{target.name}{auto}{admin}")
        print(f"      {Style.DIM}{target.file_count:,} files · {target.reclaim_hint}{Style.RESET_ALL}")
    print("-" * 72)
    print(f"  {Fore.GREEN}Safe:    {_gib(report.safe_bytes)}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}Caution: {_gib(report.caution_bytes)}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Review:  {_gib(report.review_bytes)} (user data — manual only){Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}Total reclaimable (safe+caution): {_gib(report.total_reclaimable_bytes)}{Style.RESET_ALL}")
    print("=" * 72)

    if not show_startup:
        return

    inventory = collect_startup_inventory()
    if not inventory.available:
        print(f"\n{Fore.YELLOW}Startup/service inventory unavailable: {inventory.error}{Style.RESET_ALL}")
        return
    analysis = analyze_startup(inventory.data)
    print(f"\n{Fore.CYAN}{Style.BRIGHT}BACKGROUND LOAD (observe-only){Style.RESET_ALL}")
    print("-" * 72)
    for proc in analysis["heavy_processes"][:8]:
        print(f"  {proc['memory_mb']:>8.0f} MB  {proc['label']} ×{proc['instances']}")
    if analysis["manual_service_candidates"]:
        print(f"\n  {Style.BRIGHT}Auto-start services to review (set Manual):{Style.RESET_ALL}")
        for svc in analysis["manual_service_candidates"][:10]:
            print(f"    - {svc['display_name'] or svc['name']} [{svc['state']}]")
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}Recommendations:{Style.RESET_ALL}")
    for rec in analysis["recommendations"]:
        print(f"  • {rec}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Report reclaimable space and background load; optionally clean low-risk items.",
    )
    parser.add_argument("--clean", action="store_true", help="Enable the safety-gated cleanup engine (dry-run unless --apply)")
    parser.add_argument("--apply", action="store_true", help="Actually perform cleanup (default is dry-run)")
    parser.add_argument("--delete", action="store_true", help="Hard delete instead of quarantine (irreversible)")
    parser.add_argument("--no-startup", action="store_true", help="Skip startup/service/process inventory")
    parser.add_argument("--max-files", type=int, default=None, help="Override the file cap for cleanup")
    parser.add_argument("--max-gib", type=float, default=None, help="Override the byte cap (GiB) for cleanup")
    parser.add_argument("--include-empty", action="store_true", help="Include empty/missing targets in the report")
    args = parser.parse_args(argv)

    report = scan_reclaimable_space(include_empty=args.include_empty)
    _print_report(report, show_startup=not args.no_startup)

    if not args.clean:
        print(f"\n{Style.DIM}Run with --clean to preview a safe cleanup (dry-run). "
              f"Add --apply to perform it.{Style.RESET_ALL}")
        return 0

    approved, immutable = _load_allowlist()
    from viper_health.maintenance.safe_cleanup import DEFAULT_MAX_BYTES, DEFAULT_MAX_FILES

    max_files = args.max_files if args.max_files is not None else DEFAULT_MAX_FILES
    max_bytes = int(args.max_gib * 1024**3) if args.max_gib is not None else DEFAULT_MAX_BYTES

    actions, stopped = plan_cleanup(
        report.targets,
        allowed_roots=approved,
        immutable_roots=immutable,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    mode = DELETE if args.delete else QUARANTINE
    dry_run = not args.apply

    quarantine_dir = _repo_root() / "data" / "quarantine"
    result = execute_cleanup(
        actions,
        dry_run=dry_run,
        mode=mode,
        quarantine_dir=quarantine_dir,
        manifest_dir=quarantine_dir,
        stopped_reason=stopped,
    )

    print("\n" + "=" * 72)
    banner = "DRY-RUN (nothing changed)" if dry_run else f"APPLIED ({mode})"
    color = Fore.CYAN if dry_run else (Fore.RED if mode == DELETE else Fore.GREEN)
    print(f"{color}{Style.BRIGHT}CLEANUP {banner}{Style.RESET_ALL}")
    print("=" * 72)
    print(f"  Eligible files:   {result.files_actioned:,}")
    print(f"  Reclaimable:      {_gib(result.bytes_reclaimed)}")
    print(f"  Skipped:          {result.files_skipped:,}")
    if result.stopped_reason:
        print(f"  {Fore.YELLOW}Stopped: {result.stopped_reason}{Style.RESET_ALL}")
    print(f"  Manifest:         {result.manifest_path}")
    if result.quarantine_dir:
        print(f"  Quarantine:       {result.quarantine_dir}")
    if dry_run:
        print(f"\n{Fore.YELLOW}This was a preview. Re-run with --apply to perform it "
              f"(quarantine-first; add --delete only if you are sure).{Style.RESET_ALL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
