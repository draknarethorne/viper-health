"""
Convenience wrapper for the viper-health unified scan.

Delegates to the packaged CLI so users can run a scan without remembering the
module path. Equivalent to: python -m viper_health.cli.scan

Usage:
    python scripts/invoke_scan.py --root C:\\Users\\me\\AppData --console-summary
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from viper_health.cli.scan import main as scan_main
    except ImportError:
        sys.stderr.write(
            "viper-health is not installed. From the repo root run:\n"
            "  python -m pip install -e python\n"
        )
        return 1

    return scan_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
