"""Safe helpers for read-only PowerShell JSON collection on Windows."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PowerShellJsonResult:
    """Result of a PowerShell command expected to emit JSON."""

    available: bool
    data: Any = None
    error: str | None = None


def run_powershell_json(
    script: str,
    *,
    timeout_seconds: int = 90,
) -> PowerShellJsonResult:
    """Run a non-interactive PowerShell script and decode its JSON output.

    The helper never raises for expected environment failures. Callers receive
    an explicit unavailable result for missing PowerShell, timeouts, nonzero
    exits, empty output, or malformed JSON.
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return PowerShellJsonResult(
            available=False,
            error=f"PowerShell collection timed out after {timeout_seconds} seconds",
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return PowerShellJsonResult(available=False, error=str(exc))

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return PowerShellJsonResult(
            available=False,
            error=detail or f"PowerShell exited with code {result.returncode}",
        )

    text = result.stdout.lstrip("\ufeff").strip()
    if not text:
        return PowerShellJsonResult(
            available=False,
            error="PowerShell returned no JSON data",
        )

    try:
        return PowerShellJsonResult(available=True, data=json.loads(text))
    except json.JSONDecodeError as exc:
        return PowerShellJsonResult(
            available=False,
            error=f"PowerShell returned invalid JSON: {exc}",
        )
