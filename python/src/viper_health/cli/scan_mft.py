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
        
        # Detailed recommendations
        if analysis["overall_severity"] != "good":
            print(f"{Fore.YELLOW}{Style.BRIGHT}💡 RECOMMENDATIONS & NEXT STEPS:{Style.RESET_ALL}\n")
            
            if analysis["size_severity"] == "critical":
                print(f"{Fore.RED}{Style.BRIGHT}🚨 CRITICAL: MFT Size {analysis['mft_size_gb']:.2f} GB{Style.RESET_ALL}")
                print(f"   Threshold: >2.5 GB indicates severe metadata pressure")
                print(f"   Total Files: {analysis['total_files']:,} | Folders: {analysis['total_folders']:,}")
                print(f"\n   {Style.BRIGHT}Why This Matters:{Style.RESET_ALL}")
                print("   • Every file/folder requires MFT entry (~1KB each)")
                print("   • Large MFT = slower file operations, longer boot times")
                print("   • Metadata-heavy workloads can increase random-I/O cost")
                print(f"\n   {Style.BRIGHT}Immediate Actions:{Style.RESET_ALL}")
                print("   1. Identify tiny-file hotspots:")
                print("      python -m viper_health.cli.suite --preset full-system --console-summary")
                print("   2. Target high-impact areas:")
                print("      • Browser caches (Chrome/Edge/Firefox)")
                print("      • VS Code workspace storage")
                print("      • npm/pip/NuGet package caches")
                print("      • Windows temp folders")
                print("   3. Archive or consolidate:")
                print("      • Zip old projects instead of leaving thousands of files")
                print("      • Move static data to secondary drive")
                print("   4. Re-run this read-only scan after reviewed cleanup")
                print()
            
            elif analysis["size_severity"] == "warning":
                print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  WARNING: MFT Size {analysis['mft_size_gb']:.2f} GB{Style.RESET_ALL}")
                print(f"   Threshold: >2.0 GB suggests growing metadata pressure")
                print(f"\n   {Style.BRIGHT}Recommended Actions:{Style.RESET_ALL}")
                print("   1. Run filesystem scan to identify hotspots:")
                print("      python -m viper_health.cli.suite --preset user-data")
                print("   2. Clean up high-churn areas regularly")
                print("   3. Monitor MFT size weekly to track trends")
                print()
            
            if analysis["fragmentation_severity"] == "critical":
                print(f"{Fore.RED}{Style.BRIGHT}🚨 CRITICAL: MFT Fragmentation - {analysis['mft_fragments']} fragments{Style.RESET_ALL}")
                print(f"   Threshold: >10 fragments severely impacts performance")
                print(f"\n   {Style.BRIGHT}Why This Matters:{Style.RESET_ALL}")
                print("   • Fragmented MFT = random I/O for every file operation")
                print("   • Causes slowdowns in file explorer, app launches, boot")
                print(f"\n   {Style.BRIGHT}Immediate Actions:{Style.RESET_ALL}")
                print("   1. Review Windows storage events and drive reliability")
                print("   2. Re-run this scan after resolving hardware concerns:")
                print("      python -m viper_health.cli.scan_mft --drive C:")
                print("   3. If fragmentation persists:")
                print("      • Treat it as filesystem metadata evidence, not drive failure")
                print("      • Ensure >20% free space on drive")
                print("      • Let Windows scheduled Optimize Drives manage stable SSDs")
                print()
            
            elif analysis["fragmentation_severity"] == "warning":
                print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  WARNING: MFT Fragmentation - {analysis['mft_fragments']} fragments{Style.RESET_ALL}")
                print(f"   Threshold: >5 fragments may impact performance")
                print(f"\n   {Style.BRIGHT}Recommended Actions:{Style.RESET_ALL}")
                print("   1. Monitor fragmentation and filesystem pressure monthly")
                print("   2. Do not defragment storage with unresolved fault evidence")
                print()
            
            # Additional context
            print(f"{Fore.CYAN}{Style.BRIGHT}📋 ADDITIONAL CONTEXT:{Style.RESET_ALL}")
            print(f"   {Style.BRIGHT}Post-Cleanup 'Calm Phase':{Style.RESET_ALL}")
            print("   • After deleting files, let system idle 30-60 minutes")
            print("   • Windows updates MFT and runs TRIM on deleted blocks")
            print("   • SSD garbage collection reclaims space")
            print("   • Re-run scan after calm phase to see improvements")
            print(f"\n   {Style.BRIGHT}TRIM Status Check (admin required):{Style.RESET_ALL}")
            print("   fsutil behavior query DisableDeleteNotify")
            print("   • Should show: DisableDeleteNotify = 0 (TRIM enabled)")
            print("   • If disabled (=1), enable with:")
            print("     fsutil behavior set DisableDeleteNotify 0")
            print(f"\n   {Style.BRIGHT}Related Health Checks:{Style.RESET_ALL}")
            print("   • Whole System: python -m viper_health.cli.system_report")
            print("   • Filesystem Scan: python -m viper_health.cli.suite --preset quick-check")
            print()
        
        else:
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ Excellent MFT Health!{Style.RESET_ALL}")
            print(f"   MFT Size: {analysis['mft_size_gb']:.2f} GB (healthy)")
            print(f"   Fragmentation: {analysis['mft_fragments']} fragments (healthy)")
            print("   Continue periodic monitoring to maintain health.")
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
