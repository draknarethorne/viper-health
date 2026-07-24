"""
Top disk-I/O process collector (Windows).

Identifies processes generating the most disk I/O using PowerShell performance
counters (\\Process(*)\\IO Data Bytes/sec). Helps diagnose sustained drive
activity from background services (search indexer, antivirus, cloud sync).

Read-only and best-effort: returns an empty list if counters are unavailable.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessIO:
    """Disk-I/O sample for a single process."""

    name: str
    io_bytes_per_sec: float
    io_mb_per_sec: float


def _run_powershell(script: str, timeout: int = 45) -> str | None:
    """Run a PowerShell script and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def get_top_io_processes(top_n: int = 10) -> list[ProcessIO]:
    """
    Sample current per-process disk I/O and return the top consumers.

    Args:
        top_n: Number of top processes to return.

    Returns:
        List of ProcessIO sorted by I/O descending. Empty if unavailable.
    """
    # Use the IO Data Bytes/sec counter, exclude _total and idle rollups.
    script = (
        "$c = (Get-Counter '\\Process(*)\\IO Data Bytes/sec' "
        "-ErrorAction SilentlyContinue).CounterSamples | "
        "Where-Object { $_.InstanceName -notin @('_total','idle') -and "
        "$_.CookedValue -gt 0 } | "
        "Sort-Object CookedValue -Descending | "
        f"Select-Object -First {top_n} InstanceName,CookedValue; "
        "$c | ForEach-Object { [PSCustomObject]@{ "
        "Name=$_.InstanceName; Bytes=$_.CookedValue } } | "
        "ConvertTo-Json -Compress"
    )
    out = _run_powershell(script)
    if not out:
        return []

    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []

    results: list[ProcessIO] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("Name", "unknown"))
        try:
            bytes_per_sec = float(entry.get("Bytes", 0.0))
        except (ValueError, TypeError):
            bytes_per_sec = 0.0

        results.append(
            ProcessIO(
                name=name,
                io_bytes_per_sec=round(bytes_per_sec, 1),
                io_mb_per_sec=round(bytes_per_sec / (1024 * 1024), 3),
            )
        )

    return results
