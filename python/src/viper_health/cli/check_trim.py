"""CLI for checking TRIM status."""

from __future__ import annotations

import argparse
import sys

from viper_health.collectors.trim_status import check_trim_status

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for TRIM status check."""
    parser = argparse.ArgumentParser(
        description="Viper Health TRIM Status Checker",
        epilog="""
Examples:
  # Check TRIM status (system-wide setting)
  python -m viper_health.cli.check_trim

  # Check with drive context
  python -m viper_health.cli.check_trim --drive C:
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--drive",
        type=str,
        default="C:",
        help="Drive for context (TRIM is system-wide)",
    )

    args = parser.parse_args(argv)

    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Checking TRIM Status...{Style.RESET_ALL}\n")

    try:
        status = check_trim_status(args.drive)

        # Display result
        print("="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}💾 TRIM STATUS{Style.RESET_ALL}")
        print("="*70)

        if status.trim_enabled:
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ TRIM is ENABLED{Style.RESET_ALL}")
            print(f"   DisableDeleteNotify = {status.raw_value}")
            print(f"   Status: {Fore.GREEN}GOOD{Style.RESET_ALL}")
            print()
            print(f"{Style.BRIGHT}What This Means:{Style.RESET_ALL}")
            print("   • Your SSD can efficiently reclaim deleted blocks")
            print("   • Garbage collection will work properly")
            print("   • Performance should remain stable over time")
            print()
            print(f"{Style.BRIGHT}Maintenance:{Style.RESET_ALL}")
            print("   • No action needed - TRIM is working correctly")
            print("   • Continue normal cleanup and 'calm phase' workflow")
        else:
            print(f"{Fore.RED}{Style.BRIGHT}❌ TRIM is DISABLED{Style.RESET_ALL}")
            print(f"   DisableDeleteNotify = {status.raw_value}")
            print(f"   Status: {Fore.RED}CRITICAL{Style.RESET_ALL}")
            print()
            print(f"{Fore.RED}{Style.BRIGHT}⚠️  WARNING: This is a serious issue!{Style.RESET_ALL}")
            print()
            print(f"{Style.BRIGHT}What This Means:{Style.RESET_ALL}")
            print("   • Your SSD cannot reclaim deleted blocks efficiently")
            print("   • Garbage collection is severely impaired")
            print("   • Performance will continuously degrade")
            print("   • File deletions won't improve drive speed")
            print()
            print(f"{Fore.YELLOW}{Style.BRIGHT}💡 HOW TO FIX (requires admin):{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}1. Open PowerShell or CMD as Administrator{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}2. Enable TRIM:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}fsutil behavior set DisableDeleteNotify 0{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}3. Verify it's enabled:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}fsutil behavior query DisableDeleteNotify{Style.RESET_ALL}")
            print("      (Should show: DisableDeleteNotify = 0)")
            print()
            print(f"   {Style.BRIGHT}4. Reboot system{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}5. Re-run this check to verify:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}python -m viper_health.cli.check_trim{Style.RESET_ALL}")
            print()

        print("="*70 + "\n")

        # Exit code based on status
        return 0 if status.trim_enabled else 1

    except Exception as e:
        error_msg = str(e)
        print(f"{Fore.RED}❌ Error: {error_msg}{Style.RESET_ALL}", file=sys.stderr)

        if "administrator privileges" in error_msg.lower():
            print(f"\n{Fore.YELLOW}💡 To check TRIM status:{Style.RESET_ALL}")
            print("   1. Open PowerShell or Command Prompt as Administrator")
            print("   2. Navigate to viper-health directory")
            print("   3. Run: .venv\\Scripts\\python.exe -m viper_health.cli.check_trim")

        return 1


if __name__ == "__main__":
    sys.exit(main())
