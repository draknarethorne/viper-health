"""CLI for comparing current metrics to baseline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from viper_health.analyzers.baseline_comparison import compare_to_baseline

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for baseline comparison."""
    parser = argparse.ArgumentParser(
        description="Viper Health Baseline Comparison & Trend Analysis",
        epilog="""
Examples:
  # Compare benchmark results to baseline
  python -m viper_health.cli.compare_baseline --baseline data/baselines/baseline.json --current data/benchmarks/latest.json
  
  # Compare with verbose output
  python -m viper_health.cli.compare_baseline --baseline baseline.json --current current.json --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline JSON file",
    )
    
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current results JSON file",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all metrics, not just changes",
    )
    
    args = parser.parse_args(argv)
    
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 Comparing to Baseline...{Style.RESET_ALL}\n")
    
    try:
        # Load current data
        with open(args.current) as f:
            current_data = json.load(f)
        
        # Add timestamp if not present
        if "timestamp" not in current_data:
            current_data["timestamp"] = datetime.now().isoformat()
        
        # Compare
        comparison = compare_to_baseline(current_data, args.baseline)
        
        # Determine overall color
        if comparison.overall_severity == "critical":
            overall_color = Fore.RED
            overall_icon = "❌"
        elif comparison.overall_severity == "degraded":
            overall_color = Fore.YELLOW
            overall_icon = "⚠️"
        elif comparison.overall_severity == "improved":
            overall_color = Fore.GREEN
            overall_icon = "📈"
        else:  # stable
            overall_color = Fore.GREEN
            overall_icon = "✅"
        
        # Display results
        print("="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}📈 BASELINE COMPARISON{Style.RESET_ALL}")
        print("="*70)
        print(f"Baseline: {comparison.baseline_date}")
        print(f"Current:  {comparison.current_date}")
        print()
        print(f"{Style.BRIGHT}Overall Trend:{Style.RESET_ALL}")
        print(f"  {overall_color}{Style.BRIGHT}{overall_icon} {comparison.overall_severity.upper()}{Style.RESET_ALL}")
        print("="*70 + "\n")
        
        # Show alerts
        if comparison.alerts:
            print(f"{Fore.YELLOW}{Style.BRIGHT}🚨 ALERTS:{Style.RESET_ALL}\n")
            for alert in comparison.alerts:
                print(f"   • {alert}")
            print()
        
        # Show metric changes
        if comparison.changes:
            print(f"{Style.BRIGHT}Metric Changes:{Style.RESET_ALL}\n")
            
            for change in comparison.changes:
                # Determine color and icon
                if change.severity == "critical":
                    color = Fore.RED
                    icon = "❌"
                elif change.severity == "degraded":
                    color = Fore.YELLOW
                    icon = "⚠️"
                elif change.severity == "improved":
                    color = Fore.GREEN
                    icon = "📈"
                else:  # stable
                    if args.verbose:
                        color = Fore.CYAN
                        icon = "—"
                    else:
                        continue  # Skip stable metrics unless verbose
                
                # Format change
                if change.change_percent > 0:
                    change_str = f"+{change.change_percent:.1f}%"
                else:
                    change_str = f"{change.change_percent:.1f}%"
                
                print(f"   {icon} {color}{change.metric_name.replace('_', ' ').title()}{Style.RESET_ALL}")
                print(f"      {change.baseline_value:.2f} → {change.current_value:.2f} ({change_str})")
                print(f"      Status: {color}{change.severity.upper()}{Style.RESET_ALL}")
                print()
        else:
            print(f"{Fore.CYAN}No comparable metrics found in baseline and current files.{Style.RESET_ALL}\n")
        
        # Recommendations
        if comparison.overall_severity in ("degraded", "critical"):
            print(f"{Fore.YELLOW}{Style.BRIGHT}💡 RECOMMENDATIONS:{Style.RESET_ALL}\n")
            
            if comparison.overall_severity == "critical":
                print(f"{Style.BRIGHT}Immediate Actions:{Style.RESET_ALL}")
                print("   1. Run full filesystem health scan:")
                print(f"      {Fore.CYAN}python -m viper_health.cli.suite --preset full-system{Style.RESET_ALL}")
                print()
                print("   2. Check TRIM status (requires admin):")
                print(f"      {Fore.CYAN}python -m viper_health.cli.check_trim{Style.RESET_ALL}")
                print()
                print("   3. Check free space:")
                print(f"      {Fore.CYAN}python -m viper_health.cli.check_space{Style.RESET_ALL}")
                print()
                print("   4. Run MFT analysis (requires admin):")
                print(f"      {Fore.CYAN}python -m viper_health.cli.scan_mft{Style.RESET_ALL}")
                print()
            else:  # degraded
                print(f"{Style.BRIGHT}Recommended Actions:{Style.RESET_ALL}")
                print("   1. Run targeted cleanup based on alerts above")
                print("   2. Let drive idle for 60 minutes (calm phase)")
                print("   3. Re-run benchmark to see if performance recovers")
                print("   4. Continue weekly monitoring to track trends")
                print()
        
        elif comparison.overall_severity == "improved":
            print(f"{Fore.GREEN}{Style.BRIGHT}🎉 Performance Improved!{Style.RESET_ALL}\n")
            print("   Your cleanup and maintenance efforts are working.")
            print("   Continue current workflow to maintain health.")
            print()
        
        else:  # stable
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ Performance Stable{Style.RESET_ALL}\n")
            print("   No significant changes detected.")
            print("   Continue periodic monitoring.")
            print()
        
        # Exit code based on overall severity
        if comparison.overall_severity == "critical":
            return 1
        return 0
    
    except FileNotFoundError as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
