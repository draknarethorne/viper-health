"""Passive startup, service, and background-process inventory (Windows).

Read-only. Enumerates auto-start programs (registry Run keys + Startup folder),
scheduled tasks that fire at logon/boot, auto-start services, and a grouped
snapshot of running processes by memory. Nothing is disabled or modified —
this feeds advisory recommendations only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from viper_health.utils.windows_powershell import run_powershell_json


@dataclass(frozen=True)
class StartupInventory:
    """Best-effort startup/service/process snapshot."""

    available: bool
    data: dict[str, Any]
    error: str | None = None


_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$startup = @(Get-CimInstance Win32_StartupCommand | ForEach-Object {
    [PSCustomObject]@{ Name = $_.Name; Command = $_.Command; Location = $_.Location; User = $_.User }
})
$tasks = @(Get-ScheduledTask | Where-Object { $_.State -eq 'Ready' -and (
        $_.Triggers | Where-Object { $_.CimClass.CimClassName -match 'Logon|Boot' }
    ) } | ForEach-Object {
    [PSCustomObject]@{ TaskName = $_.TaskName; TaskPath = $_.TaskPath; State = [string]$_.State }
})
$services = @(Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq 'Auto' } | ForEach-Object {
    [PSCustomObject]@{ Name = $_.Name; DisplayName = $_.DisplayName; State = $_.State; StartMode = $_.StartMode }
})
$procs = @(Get-Process | Group-Object -Property ProcessName | ForEach-Object {
    [PSCustomObject]@{
        Name = $_.Name
        Count = $_.Count
        WorkingSetBytes = ($_.Group | Measure-Object -Property WorkingSet64 -Sum).Sum
    }
} | Sort-Object WorkingSetBytes -Descending | Select-Object -First 25)
[PSCustomObject]@{
    StartupCommands = $startup
    ScheduledTasks = $tasks
    Services = $services
    Processes = $procs
} | ConvertTo-Json -Depth 5 -Compress
"""


def collect_startup_inventory() -> StartupInventory:
    """Collect a passive startup/service/process snapshot via PowerShell."""
    result = run_powershell_json(_SCRIPT, timeout_seconds=120)
    if not result.available or not isinstance(result.data, dict):
        return StartupInventory(
            available=False,
            data={},
            error=result.error or "Startup inventory was unavailable",
        )
    return StartupInventory(available=True, data=result.data)
