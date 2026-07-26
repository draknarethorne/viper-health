"""Standalone CLI for the advisory machine-capability assessment.

Collects passive system specifications and prints a capability tier plus
optimization recommendations. This is advisory context about how well-provisioned
the machine is; it is separate from fault-evidence health (see ``system_report``).
"""

from __future__ import annotations

import argparse
import json
import sys

from viper_health.analyzers.spec_assessment import assess_system_capability
from viper_health.collectors.system_inventory import collect_system_inventory

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except ImportError:  # pragma: no cover - color is cosmetic
    class Fore:
        GREEN = YELLOW = RED = CYAN = RESET = ""

    class Style:
        BRIGHT = RESET_ALL = ""


_TIER_COLOR = {
    "solid": Fore.GREEN,
    "capable": Fore.GREEN,
    "dated": Fore.YELLOW,
    "weak": Fore.RED,
    "unknown": Fore.CYAN,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the capability assessment."""
    parser = argparse.ArgumentParser(
        description="Advisory machine-capability assessment from passive specifications.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the raw capability JSON")
    args = parser.parse_args(argv)

    inventory = collect_system_inventory().to_dict()
    capability = assess_system_capability(inventory)

    if args.json:
        print(json.dumps(capability, indent=2))
        return 0

    tier = str(capability.get("tier", "unknown"))
    color = _TIER_COLOR.get(tier, Fore.CYAN)

    print("=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}MACHINE CAPABILITY (advisory){Style.RESET_ALL}")
    print("=" * 70)
    print(f"  {color}{Style.BRIGHT}Overall: {tier.upper()}{Style.RESET_ALL}")
    print(f"  {capability.get('summary', '')}")
    print()

    components = capability.get("components") or {}
    if components:
        print(f"{Style.BRIGHT}Components:{Style.RESET_ALL}")
        for name, comp in components.items():
            if not isinstance(comp, dict):
                continue
            comp_tier = str(comp.get("tier", "unknown"))
            comp_color = _TIER_COLOR.get(comp_tier, Fore.CYAN)
            print(f"  {comp_color}{name:<12} {comp_tier.upper()}{Style.RESET_ALL}")
            for note in comp.get("notes", []):
                print(f"      - {note}")
        print()

    recommendations = capability.get("recommendations") or []
    if recommendations:
        print(f"{Fore.YELLOW}{Style.BRIGHT}Optimization recommendations:{Style.RESET_ALL}")
        for recommendation in recommendations:
            print(f"  • {recommendation}")
        print()

    print("Note: capability is advisory and separate from fault-evidence health.")
    print("Run `python -m viper_health.cli.system_report` for fault evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
