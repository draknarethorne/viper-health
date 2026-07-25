"""CLI for drive health / SMART / temperature (spec: drive health monitoring)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from viper_health.collectors.smart_data import (
    LIMITED_PASSTHROUGH_BUSES,
    DriveHealth,
    get_drive_health,
    is_elevated,
)

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
    return {"good": "✅", "warning": "⚠️", "critical": "❌"}.get(severity, "❓")


def _print_drive(d: DriveHealth) -> None:
    color = _severity_color(d.severity)
    icon = _severity_icon(d.severity)

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}💽 {d.friendly_name}{Style.RESET_ALL}")
    print("=" * 70)
    print(f"  Device ID:     {d.device_id}")
    print(f"  Media Type:    {d.media_type}")
    print(f"  Bus Type:      {d.bus_type}")
    print(f"  Health Status: {d.health_status}")

    if d.temperature_c is not None:
        tcolor = _severity_color(
            "critical" if d.temperature_c >= 70 else
            "warning" if d.temperature_c >= 55 else "good"
        )
        print(f"  Temperature:   {tcolor}{d.temperature_c:.0f}°C{Style.RESET_ALL}")
    else:
        print("  Temperature:   (unavailable)")

    if d.wear_percent is not None:
        print(f"  Wear (used):   {d.wear_percent:.0f}%")
    if d.power_on_hours is not None:
        print(f"  Power-On:      {d.power_on_hours:,} hours")
    if d.read_errors_total is not None:
        print(f"  Read Errors:   {d.read_errors_total:,}")
    if d.write_errors_total is not None:
        print(f"  Write Errors:  {d.write_errors_total:,}")

    # Explain why the deeper metrics are missing rather than silently hiding it.
    if not d.reliability_available:
        limited_bus = d.bus_type.strip().lower() in LIMITED_PASSTHROUGH_BUSES
        print(
            f"  {Fore.YELLOW}Reliability:   wear/temp/power-on unavailable"
            f"{Style.RESET_ALL}"
        )
        if limited_bus:
            print(
                f"                 {Fore.YELLOW}drive is behind {d.bus_type} "
                f"(Intel RST/VMD) — SMART passthrough limited{Style.RESET_ALL}"
            )

    print(f"  {color}{icon} Status: {d.severity.upper()}{Style.RESET_ALL}")
    print("=" * 70 + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for drive health / SMART check."""
    parser = argparse.ArgumentParser(
        description="Viper Health Drive Health / SMART / Temperature Check",
        epilog="""
Examples:
  # Check all physical disks
  python -m viper_health.cli.check_smart

  # Save results
  python -m viper_health.cli.check_smart --output smart.json

Note: Uses Windows Storage cmdlets. Some fields (temperature, wear) may be
unavailable depending on drive/firmware. Run elevated for best results.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output", type=Path, help="Save results to JSON file")

    args = parser.parse_args(argv)

    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Querying drive health...{Style.RESET_ALL}\n")

    drives = get_drive_health()

    if not drives:
        print(
            f"{Fore.YELLOW}⚠️  No drive health data available.{Style.RESET_ALL}\n"
            "   Windows Storage cmdlets returned nothing. This can happen when:\n"
            "   • Running without administrator privileges\n"
            "   • Drive/firmware doesn't expose reliability counters\n"
            "   • Storage subsystem doesn't support Get-StorageReliabilityCounter\n\n"
            f"{Fore.CYAN}💡 Alternative:{Style.RESET_ALL} Use CrystalDiskInfo or "
            "HWiNFO64 for detailed SMART attributes."
        )
        return 0

    worst = "good"
    for d in drives:
        _print_drive(d)
        if d.severity == "critical":
            worst = "critical"
        elif d.severity == "warning" and worst != "critical":
            worst = "warning"

    color = _severity_color(worst)
    print(f"{Style.BRIGHT}Overall Drive Health: {color}{worst.upper()}{Style.RESET_ALL}")

    if worst == "critical":
        print(
            f"\n{Fore.RED}{Style.BRIGHT}🚨 CRITICAL drive condition detected!{Style.RESET_ALL}\n"
            "   • Back up important data immediately\n"
            "   • Check temperature/cooling if thermal\n"
            "   • Run vendor diagnostic tool\n"
            "   • Consider drive replacement if wear/errors are high"
        )
    elif worst == "warning":
        print(
            f"\n{Fore.YELLOW}💡 Monitor closely:{Style.RESET_ALL}\n"
            "   • Improve airflow if temperature is elevated\n"
            "   • Re-check after reducing sustained I/O load\n"
            "   • Track wear percentage over time"
        )
    else:
        print(f"\n{Fore.GREEN}✅ All drives report healthy.{Style.RESET_ALL}")

    # Explain how to unlock wear/temperature/power-on data when it's missing.
    missing_reliability = [d for d in drives if not d.reliability_available]
    if missing_reliability:
        elevated = is_elevated()
        limited_buses = sorted({
            d.bus_type for d in missing_reliability
            if d.bus_type.strip().lower() in LIMITED_PASSTHROUGH_BUSES
        })

        print(
            f"\n{Fore.YELLOW}{Style.BRIGHT}ℹ️  Wear / temperature / power-on data "
            f"unavailable for {len(missing_reliability)} drive(s).{Style.RESET_ALL}"
        )
        print("   These NVMe/SATA reliability counters are not readable here because:")
        if elevated is False:
            print(f"   • {Fore.YELLOW}Not running as Administrator{Style.RESET_ALL} "
                  "— reliability counters require elevation.")
            print("     Re-run from an elevated terminal:")
            print("       python -m viper_health.cli.check_smart")
        elif elevated is None:
            print("   • Elevation status could not be determined; try an "
                  "elevated terminal.")
        else:
            print(f"   • {Fore.GREEN}Running elevated{Style.RESET_ALL}, so the "
                  "storage driver itself is not exposing the counters.")
        if limited_buses:
            print(f"   • One or more drives sit behind "
                  f"{Fore.YELLOW}{', '.join(limited_buses)}{Style.RESET_ALL} "
                  "(Intel RST / VMD).")
            print("     RAID/VMD controllers commonly block SMART passthrough,")
            print("     so wear/TBW may be unreadable even when elevated.")
        print(
            f"\n   {Fore.CYAN}To confirm drive age/wear (Power-On Hours, TBW, "
            f"Health %):{Style.RESET_ALL}"
        )
        print("   • CrystalDiskInfo or `smartctl -d nvme` read SMART through the "
              "RST driver.")

    if args.output:
        payload = {
            "drives": [asdict(d) for d in drives],
            "overall_severity": worst,
            "elevated": is_elevated(),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\n{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")

    return 1 if worst == "critical" else 0


if __name__ == "__main__":
    sys.exit(main())
