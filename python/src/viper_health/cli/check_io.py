"""CLI for top disk-I/O processes (spec: background I/O monitoring)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from viper_health.collectors.io_processes import get_top_io_processes

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


# Processes commonly responsible for sustained background disk I/O
_KNOWN_NOISY = {
    "searchindexer": "Windows Search indexing",
    "msmpeng": "Microsoft Defender scanning",
    "onedrive": "OneDrive sync",
    "googledrivefs": "Google Drive sync",
    "dropbox": "Dropbox sync",
    "svchost": "Windows service host (Update/telemetry)",
    "tiworker": "Windows module installer",
    "compattelrunner": "Windows telemetry",
    "backgroundtaskhost": "UWP background tasks",
}


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for top I/O process check."""
    parser = argparse.ArgumentParser(
        description="Viper Health Top Disk-I/O Process Monitor",
        epilog="""
Examples:
  # Show top 10 I/O processes
  python -m viper_health.cli.check_io

  # Show top 20 and save
  python -m viper_health.cli.check_io --top 20 --output io.json

Note: Samples a single instant of the IO Data Bytes/sec counter. Run a few
times to see sustained patterns.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--top", type=int, default=10, help="Number of processes (default 10)")
    parser.add_argument("--output", type=Path, help="Save results to JSON file")

    args = parser.parse_args(argv)

    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Sampling process disk I/O...{Style.RESET_ALL}\n")

    procs = get_top_io_processes(top_n=args.top)

    if not procs:
        print(
            f"{Fore.YELLOW}⚠️  No process I/O data available.{Style.RESET_ALL}\n"
            "   Performance counters returned nothing. Try running elevated, or\n"
            "   use Resource Monitor (resmon) → Disk tab for live per-process I/O."
        )
        return 0

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 TOP DISK-I/O PROCESSES{Style.RESET_ALL}")
    print("=" * 70)

    for i, p in enumerate(procs, start=1):
        note = _KNOWN_NOISY.get(p.name.lower(), "")
        note_str = f"  {Fore.YELLOW}({note}){Style.RESET_ALL}" if note else ""
        print(f"  {i:2}. {Style.BRIGHT}{p.name}{Style.RESET_ALL}{note_str}")
        print(f"      {p.io_mb_per_sec:.2f} MB/s ({p.io_bytes_per_sec:,.0f} bytes/s)")

    print("=" * 70)
    print(
        f"\n{Fore.CYAN}💡 Tip:{Style.RESET_ALL} If a background process dominates I/O, "
        "it may be causing latency.\n"
        "   Common culprits: search indexer, antivirus, cloud sync, Windows Update."
    )

    if args.output:
        payload = {"processes": [asdict(p) for p in procs]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\n{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
