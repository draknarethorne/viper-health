"""CLI for checking disk space."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.collectors.disk_space import analyze_disk_space, format_disk_space_summary

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for disk space check."""
    parser = argparse.ArgumentParser(
        description="Viper Health Disk Space Monitor",
        epilog="""
Examples:
  # Check C: drive free space
  python -m viper_health.cli.check_space
  
  # Check D: drive
  python -m viper_health.cli.check_space --drive D:
  
  # Save results
  python -m viper_health.cli.check_space --output space_check.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--drive",
        type=str,
        default="C:",
        help="Drive to check (default: C:)",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )
    
    args = parser.parse_args(argv)
    
    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Checking Disk Space for {args.drive}...{Style.RESET_ALL}\n")
    
    try:
        info = analyze_disk_space(args.drive)
        summary = format_disk_space_summary(info)
        
        # Determine color and icon
        if info.severity == "good":
            status_color = Fore.GREEN
            status_icon = "✅"
        elif info.severity == "warning":
            status_color = Fore.YELLOW
            status_icon = "⚠️"
        else:  # critical
            status_color = Fore.RED
            status_icon = "❌"
        
        # Display results
        print("="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}💾 DISK SPACE ANALYSIS{Style.RESET_ALL}")
        print("="*70)
        print(f"Drive: {info.drive}")
        print()
        print(f"{Style.BRIGHT}Space Usage:{Style.RESET_ALL}")
        print(f"  Total: {summary['total_gb']:.2f} GB")
        print(f"  Used: {summary['used_gb']:.2f} GB")
        print(f"  Free: {summary['free_gb']:.2f} GB ({info.free_percent:.1f}%)")
        print()
        print(f"{Style.BRIGHT}Health Assessment:{Style.RESET_ALL}")
        print(f"  {status_color}{Style.BRIGHT}{status_icon} Status: {info.severity.upper()}{Style.RESET_ALL}")
        print("="*70 + "\n")
        
        # Recommendations
        if info.severity == "critical":
            print(f"{Fore.RED}{Style.BRIGHT}🚨 CRITICAL: Less than 10% free space!{Style.RESET_ALL}\n")
            print(f"{Style.BRIGHT}Why This is Urgent:{Style.RESET_ALL}")
            print("   • SSDs need free space for wear leveling and garbage collection")
            print("   • QLC drives especially need headroom (15-20% minimum)")
            print("   • Performance will degrade rapidly")
            print("   • SLC cache size is reduced when space is low")
            print()
            print(f"{Fore.YELLOW}{Style.BRIGHT}💡 IMMEDIATE ACTIONS:{Style.RESET_ALL}\n")
            print(f"   {Style.BRIGHT}1. Identify large files/folders:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}Get-ChildItem C:\\ -Recurse -Directory | Sort-Object @{{Expression={{(Get-ChildItem $_.FullName -Recurse | Measure-Object Length -Sum).Sum}}; Descending=$true}} | Select-Object -First 20{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}2. Run filesystem scan to find hotspots:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}python -m viper_health.cli.suite --preset full-system --console-summary{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}3. Clear Windows temp files:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}cleanmgr /d C:{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}4. Move large files to secondary drive{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}5. Delete old Windows.old folders (if present){Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}Target: Get to 20%+ free space{Style.RESET_ALL}")
            print()
        
        elif info.severity == "warning":
            print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  WARNING: 10-20% free space{Style.RESET_ALL}\n")
            print(f"{Style.BRIGHT}What This Means:{Style.RESET_ALL}")
            print("   • Drive approaching critical free space threshold")
            print("   • Performance may start to degrade")
            print("   • SLC cache capacity reduced")
            print()
            print(f"{Fore.YELLOW}{Style.BRIGHT}💡 RECOMMENDED ACTIONS:{Style.RESET_ALL}\n")
            print(f"   {Style.BRIGHT}1. Run filesystem scan:{Style.RESET_ALL}")
            print(f"      {Fore.CYAN}python -m viper_health.cli.suite --preset user-data{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}2. Clean up temporary files and caches{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}3. Archive old projects (zip instead of thousands of files){Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}4. Move static data to secondary storage{Style.RESET_ALL}")
            print()
            print(f"   {Style.BRIGHT}Target: Get to 25%+ free space for optimal performance{Style.RESET_ALL}")
            print()
        
        else:  # good
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ Healthy Free Space!{Style.RESET_ALL}\n")
            print(f"   Your drive has adequate free space ({info.free_percent:.1f}%)")
            print(f"   Continue periodic monitoring to maintain health.")
            print()
        
        # Save to JSON if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2)
            
            print(f"{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")
        
        # Exit code based on severity
        if info.severity == "critical":
            return 1
        return 0
    
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
