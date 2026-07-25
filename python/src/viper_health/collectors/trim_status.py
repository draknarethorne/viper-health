"""
TRIM status verification for Windows drives.

TRIM (or UNMAP) is critical for SSD health - it tells the drive which blocks
are no longer in use so garbage collection can reclaim them efficiently.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class TRIMStatus:
    """TRIM status information for a drive."""
    
    drive: str
    trim_enabled: bool
    raw_value: int  # 0 = enabled, 1 = disabled
    severity: str  # "good" | "critical"


def check_trim_status(drive: str = "C:") -> TRIMStatus:
    """
    Check if TRIM is enabled for the system.
    
    Uses Windows fsutil to query DisableDeleteNotify setting.
    - 0 = TRIM enabled (good)
    - 1 = TRIM disabled (critical issue)
    
    Args:
        drive: Drive letter (used for context, TRIM is system-wide)
    
    Returns:
        TRIMStatus with enabled status and severity
    
    Raises:
        RuntimeError: If fsutil command fails
    """
    try:
        result = subprocess.run(
            ["fsutil", "behavior", "query", "DisableDeleteNotify"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            # Check for elevation requirement
            if result.returncode == 5 or "Access is denied" in result.stderr:
                raise RuntimeError(
                    "TRIM status check requires administrator privileges. "
                    "Please run from an elevated command prompt/PowerShell."
                )
            raise RuntimeError(f"fsutil command failed with exit code {result.returncode}")
        
        # Parse output
        # Modern Windows fsutil emits one line per filesystem with a trailing
        # description, e.g.:
        #   NTFS DisableDeleteNotify = 0  (Allows TRIM operations ...)
        #   ReFS DisableDeleteNotify = 1  (Disables TRIM operations ...)
        # Older Windows emits a single bare line:
        #   DisableDeleteNotify = 0
        output = result.stdout.strip()

        # Collect (filesystem, value) pairs, extracting only the leading
        # integer after '=' so trailing descriptive text is ignored.
        matches = re.findall(
            r"(?:(\w+)\s+)?DisableDeleteNotify\s*=\s*(\d+)",
            output,
        )

        if matches:
            # Prefer the NTFS line when present (primary filesystem for TRIM),
            # otherwise fall back to the first parseable value.
            selected = next(
                (m for m in matches if (m[0] or "").upper() == "NTFS"),
                matches[0],
            )
            raw_value = int(selected[1])

            # 0 = TRIM enabled (DeleteNotify NOT disabled)
            # 1 = TRIM disabled (DeleteNotify IS disabled)
            trim_enabled = (raw_value == 0)
            severity = "good" if trim_enabled else "critical"

            return TRIMStatus(
                drive=drive,
                trim_enabled=trim_enabled,
                raw_value=raw_value,
                severity=severity,
            )

        # If we couldn't parse, raise error
        raise RuntimeError(f"Could not parse fsutil output: {output}")
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to check TRIM status: {e}")
    except ValueError as e:
        raise RuntimeError(f"Failed to parse TRIM status value: {e}")
    except Exception as e:
        raise RuntimeError(f"Error checking TRIM status: {e}")
