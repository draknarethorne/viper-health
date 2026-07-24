"""
SMART and temperature collector for physical disks (Windows).

Queries drive health, temperature, and wear via PowerShell Storage cmdlets
(Get-PhysicalDisk, Get-StorageReliabilityCounter). Degrades gracefully when
data is unavailable (missing cmdlets, non-admin, or unsupported hardware).

Thresholds:
- Temperature: <55C good, 55-70C warning, >70C critical
- Wear (SSD % used): <70 good, 70-90 warning, >90 critical
- HealthStatus: "Healthy" good, "Warning" warning, otherwise critical
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DriveHealth:
    """Health/SMART summary for a single physical disk."""

    device_id: str
    friendly_name: str
    media_type: str
    health_status: str
    temperature_c: float | None
    wear_percent: float | None
    power_on_hours: int | None
    read_errors_total: int | None
    write_errors_total: int | None
    severity: str  # "good" | "warning" | "critical" | "unknown"


# Temperature thresholds (Celsius)
TEMP_WARNING_C = 55.0
TEMP_CRITICAL_C = 70.0

# Wear thresholds (percent used)
WEAR_WARNING = 70.0
WEAR_CRITICAL = 90.0


def _run_powershell(script: str) -> str | None:
    """Run a PowerShell script and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _as_list(parsed: object) -> list[dict]:
    """Normalize PowerShell JSON (object or array) into a list of dicts."""
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [p for p in parsed if isinstance(p, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _assess_severity(
    health_status: str,
    temperature_c: float | None,
    wear_percent: float | None,
) -> str:
    """Combine health signals into an overall severity."""
    severities: list[str] = []

    hs = (health_status or "").strip().lower()
    if hs == "healthy":
        severities.append("good")
    elif hs == "warning":
        severities.append("warning")
    elif hs in ("", "unknown"):
        severities.append("unknown")
    else:
        severities.append("critical")

    if temperature_c is not None:
        if temperature_c >= TEMP_CRITICAL_C:
            severities.append("critical")
        elif temperature_c >= TEMP_WARNING_C:
            severities.append("warning")
        else:
            severities.append("good")

    if wear_percent is not None:
        if wear_percent >= WEAR_CRITICAL:
            severities.append("critical")
        elif wear_percent >= WEAR_WARNING:
            severities.append("warning")
        else:
            severities.append("good")

    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "warning"
    if "good" in severities:
        return "good"
    return "unknown"


def _to_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: object) -> int | None:
    f = _to_float(value)
    return int(f) if f is not None else None


def get_drive_health() -> list[DriveHealth]:
    """
    Query physical disk health and SMART-derived metrics.

    Returns:
        List of DriveHealth entries (one per physical disk). Empty list if
        storage cmdlets are unavailable.
    """
    # Collect physical disks with health + media type
    disk_script = (
        "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,"
        "HealthStatus | ConvertTo-Json -Compress"
    )
    disk_out = _run_powershell(disk_script)

    disks: list[dict] = []
    if disk_out:
        try:
            disks = _as_list(json.loads(disk_out))
        except json.JSONDecodeError:
            disks = []

    # Collect reliability counters (temperature, wear, errors)
    rel_script = (
        "Get-PhysicalDisk | ForEach-Object { "
        "$c = $_ | Get-StorageReliabilityCounter; "
        "[PSCustomObject]@{ DeviceId=$_.DeviceId; "
        "Temperature=$c.Temperature; Wear=$c.Wear; "
        "PowerOnHours=$c.PowerOnHours; "
        "ReadErrorsTotal=$c.ReadErrorsTotal; "
        "WriteErrorsTotal=$c.WriteErrorsTotal } } | ConvertTo-Json -Compress"
    )
    rel_out = _run_powershell(rel_script)

    reliability: dict[str, dict] = {}
    if rel_out:
        try:
            for entry in _as_list(json.loads(rel_out)):
                dev = str(entry.get("DeviceId", ""))
                reliability[dev] = entry
        except json.JSONDecodeError:
            pass

    results: list[DriveHealth] = []
    for disk in disks:
        device_id = str(disk.get("DeviceId", ""))
        rel = reliability.get(device_id, {})

        temperature_c = _to_float(rel.get("Temperature"))
        wear_percent = _to_float(rel.get("Wear"))
        health_status = str(disk.get("HealthStatus", "Unknown"))

        # MediaType may be numeric or string depending on OS
        media_raw = disk.get("MediaType", "Unknown")
        media_type = {3: "HDD", 4: "SSD", 5: "SCM"}.get(media_raw, str(media_raw))

        severity = _assess_severity(health_status, temperature_c, wear_percent)

        results.append(
            DriveHealth(
                device_id=device_id,
                friendly_name=str(disk.get("FriendlyName", "Unknown")),
                media_type=media_type,
                health_status=health_status,
                temperature_c=temperature_c,
                wear_percent=wear_percent,
                power_on_hours=_to_int(rel.get("PowerOnHours")),
                read_errors_total=_to_int(rel.get("ReadErrorsTotal")),
                write_errors_total=_to_int(rel.get("WriteErrorsTotal")),
                severity=severity,
            )
        )

    return results
