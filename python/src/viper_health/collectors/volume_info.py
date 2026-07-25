"""Mounted-volume inventory for cross-machine storage profiles (Windows)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeInfo:
    """Stable capacity and filesystem facts for a mounted volume."""

    drive: str
    label: str
    filesystem: str
    drive_type: str
    health_status: str
    total_bytes: int
    free_bytes: int
    free_percent: float


def _as_records(value: object) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def get_volume_info() -> list[VolumeInfo]:
    """Return mounted volumes with drive letters, capacity, and filesystem data.

    This collector is best-effort. An empty list is returned when PowerShell or
    ``Get-Volume`` is unavailable so profile capture never fails solely because
    volume inventory could not be collected.
    """
    script = (
        "Get-Volume | Where-Object { $null -ne $_.DriveLetter } | "
        "Select-Object DriveLetter,FileSystemLabel,FileSystem,DriveType,"
        "HealthStatus,Size,SizeRemaining | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        records = _as_records(json.loads(result.stdout))
    except json.JSONDecodeError:
        return []

    volumes: list[VolumeInfo] = []
    for record in records:
        try:
            total = int(record.get("Size") or 0)
            free = int(record.get("SizeRemaining") or 0)
            free_percent = round((free / total * 100.0), 1) if total else 0.0
            letter = str(record.get("DriveLetter") or "").strip()
            if not letter:
                continue
            volumes.append(
                VolumeInfo(
                    drive=f"{letter.upper()}:",
                    label=str(record.get("FileSystemLabel") or ""),
                    filesystem=str(record.get("FileSystem") or "Unknown"),
                    drive_type=str(record.get("DriveType") or "Unknown"),
                    health_status=str(record.get("HealthStatus") or "Unknown"),
                    total_bytes=total,
                    free_bytes=free,
                    free_percent=free_percent,
                )
            )
        except (TypeError, ValueError):
            continue

    return sorted(volumes, key=lambda volume: volume.drive)
