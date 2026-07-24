"""
Disk space monitoring with threshold-based health assessment.

SSDs (especially QLC) need 15-20% free space for optimal performance.
Free space is required for wear leveling, garbage collection, and SLC cache.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiskSpaceInfo:
    """Disk space information with health assessment."""
    
    drive: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    free_percent: float
    severity: str  # "good" | "warning" | "critical"


def analyze_disk_space(drive: str = "C:") -> DiskSpaceInfo:
    """
    Analyze disk space and assess health based on free space thresholds.
    
    Thresholds:
    - <10% free = CRITICAL (immediate action needed)
    - 10-20% free = WARNING (clean up soon)
    - >20% free = GOOD (healthy)
    
    Args:
        drive: Drive path (e.g., "C:" or "C:\\")
    
    Returns:
        DiskSpaceInfo with space metrics and severity
    
    Raises:
        RuntimeError: If drive not found or inaccessible
    """
    # Normalize drive path
    if drive.endswith(":"):
        drive_path = drive + "\\"
    else:
        drive_path = drive
    
    try:
        # Get disk usage
        usage = shutil.disk_usage(drive_path)
        
        total_bytes = usage.total
        used_bytes = usage.used
        free_bytes = usage.free
        
        # Calculate free percentage
        free_percent = (free_bytes / total_bytes) * 100 if total_bytes > 0 else 0.0
        
        # Determine severity
        if free_percent < 10:
            severity = "critical"
        elif free_percent < 20:
            severity = "warning"
        else:
            severity = "good"
        
        return DiskSpaceInfo(
            drive=drive,
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            free_percent=round(free_percent, 1),
            severity=severity,
        )
    
    except FileNotFoundError:
        raise RuntimeError(f"Drive not found: {drive}")
    except PermissionError:
        raise RuntimeError(f"Access denied to drive: {drive}")
    except Exception as e:
        raise RuntimeError(f"Error analyzing disk space for {drive}: {e}")


def bytes_to_gb(bytes_value: int) -> float:
    """Convert bytes to gigabytes."""
    return bytes_value / (1024 ** 3)


def format_disk_space_summary(info: DiskSpaceInfo) -> dict[str, any]:
    """
    Format disk space info as a summary dictionary.
    
    Returns:
        Dictionary with human-readable values
    """
    return {
        "drive": info.drive,
        "total_gb": round(bytes_to_gb(info.total_bytes), 2),
        "used_gb": round(bytes_to_gb(info.used_bytes), 2),
        "free_gb": round(bytes_to_gb(info.free_bytes), 2),
        "free_percent": info.free_percent,
        "severity": info.severity,
    }
