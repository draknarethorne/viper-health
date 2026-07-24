"""CLI for MFT (Master File Table) health analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from viper_health.collectors.mft_info import analyze_mft_health, get_mft_info

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for MFT analysis."""
    parser = argparse.ArgumentParser(
        description="Viper Health MFT (Master File Table) Health Analysis",
        epilog="""
Examples:
  # Analyze C: drive MFT
  python -m viper_health.cli.scan_mft

  # Analyze D: drive
  python -m viper_health.cli.scan_mft --drive D:

  # Save results to JSON
  python -m viper_health.cli.scan_mft --output mft_health.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--drive",
        type=str,
        default="C:",
        help="Drive to analyze (default: C:)",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )
    
    args = parser.parse_args(argv)
    
    # Ensure drive format
    drive = args.drive.upper()
    if not drive.endswith(":"):
        drive += ":"
    
    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 Analyzing MFT for {drive}...{Style.RESET_ALL}\n")
    
    try:
        # Get MFT info
        mft_info = get_mft_info(drive)
        
        # Analyze health
        analysis = analyze_mft_health(mft_info)
        
        # Determine colors
        if analysis["overall_severity"] == "good":
            status_color = Fore.GREEN
            status_icon = "✅"
        elif analysis["overall_severity"] == "warning":
            status_color = Fore.YELLOW
            status_icon = "⚠️"
        else:  # critical
            status_color = Fore.RED
            status_icon = "❌"
        
        # Display results
        print("="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}📊 MFT HEALTH ANALYSIS{Style.RESET_ALL}")
        print("="*70)
        print(f"Drive: {analysis['drive']}")
        print()
        print(f"{Style.BRIGHT}MFT Metrics:{Style.RESET_ALL}")
        print(f"  MFT Size: {analysis['mft_size_gb']:.2f} GB ({analysis['mft_size_bytes']:,} bytes)")
        print(f"  MFT Fragments: {analysis['mft_fragments']}")
        print(f"  Total Files: {analysis['total_files']:,}")
        print(f"  Total Folders: {analysis['total_folders']:,}")
        print()
        print(f"{Style.BRIGHT}Health Assessment:{Style.RESET_ALL}")
        print(f"  Size Status: {analysis['size_severity'].upper()}")
        print(f"  Fragmentation Status: {analysis['fragmentation_severity'].upper()}")
        print(f"  {status_color}{Style.BRIGHT}{status_icon} Overall: {analysis['overall_severity'].upper()}{Style.RESET_ALL}")
        print("="*70 + "\n")
        
        # Recommendations
        if analysis["overall_severity"] != "good":
            print(f"{Fore.YELLOW}💡 Recommendations:{Style.RESET_ALL}")
            
            if analysis["size_severity"] != "good":
                print(f"  • MFT size is {analysis['size_severity']} ({analysis['mft_size_gb']:.2f} GB)")
                print("    Consider reducing file count or archiving unused files")
            
            if analysis["fragmentation_severity"] != "good":
                print(f"  • MFT fragmentation is {analysis['fragmentation_severity']} ({analysis['mft_fragments']} fragments)")
                print("    Consider running defragmentation on the MFT")
            
            print()
        
        # Save to JSON if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(analysis, f, indent=2)
            
            print(f"{Fore.GREEN}✅ Results saved to {args.output}{Style.RESET_ALL}")
        
        # Exit code based on severity
        if analysis["overall_severity"] == "critical":
            return 1
        return 0
    
    except Exception as e:
        error_msg = str(e)
        print(f"{Fore.RED}❌ Error: {error_msg}{Style.RESET_ALL}", file=sys.stderr)
        
        if "administrator privileges" in error_msg.lower():
            print(f"\n{Fore.YELLOW}💡 To run MFT analysis:{Style.RESET_ALL}")
            print("   1. Open PowerShell or Command Prompt as Administrator")
            print("   2. Navigate to the viper-health directory")
            print("   3. Run: .venv\\Scripts\\python.exe -m viper_health.cli.scan_mft")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
