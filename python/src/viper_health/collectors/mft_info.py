"""
MFT (Master File Table) health analysis for Windows NTFS filesystems.

Collects MFT size, fragmentation, and metadata pressure indicators.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MFTInfo:
    """MFT (Master File Table) health information."""
    
    drive: str
    mft_size_bytes: int
    mft_fragments: int
    total_files: int
    total_folders: int


def get_mft_info(drive: str = "C:") -> MFTInfo:
    """
    Get MFT information for a drive using Windows fsutil.
    
    Args:
        drive: Drive letter with colon (e.g., "C:")
    
    Returns:
        MFTInfo with MFT health data
    
    Raises:
        RuntimeError: If fsutil command fails
        ValueError: If drive format invalid
    """
    if not drive.endswith(":"):
        raise ValueError(f"Drive must end with colon (e.g., 'C:'), got: {drive}")
    
    try:
        # Get MFT info using fsutil
        result = subprocess.run(
            ["fsutil", "fsinfo", "ntfsinfo", drive],
            capture_output=True,
            text=True,
            check=False,  # Don't raise immediately, check returncode manually
        )
        
        # Check for access denied (exit code 5 on Windows)
        if result.returncode == 5 or result.returncode == 1:
            raise RuntimeError(
                f"MFT analysis requires administrator privileges. "
                f"Please run from an elevated command prompt/PowerShell."
            )
        elif result.returncode != 0:
            raise RuntimeError(f"fsutil command failed with exit code {result.returncode}")
        
        output = result.stdout
        
        # Parse output
        mft_size = 0
        mft_fragments = 0
        total_files = 0
        total_folders = 0
        
        for line in output.splitlines():
            line = line.strip()
            
            if "Mft Valid Data Length" in line:
                # Format: "Mft Valid Data Length :       0x0000000012345678"
                parts = line.split(":")
                if len(parts) >= 2:
                    hex_value = parts[1].strip()
                    mft_size = int(hex_value, 16)
            
            elif "Mft Zone Size" in line:
                # Fallback if Valid Data Length not found
                if mft_size == 0:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        hex_value = parts[1].strip()
                        mft_size = int(hex_value, 16)
            
            elif "File Records" in line and "In Use" not in line:
                # Format: "File Records                 :       123456"
                parts = line.split(":")
                if len(parts) >= 2:
                    total_files = int(parts[1].strip())
            
            elif "Folders" in line:
                # Format: "Folders                      :       12345"
                parts = line.split(":")
                if len(parts) >= 2:
                    total_folders = int(parts[1].strip())
        
        # Get fragmentation info using fsutil (may require elevation)
        try:
            frag_result = subprocess.run(
                ["fsutil", "file", "layout", f"{drive}\\$MFT"],
                capture_output=True,
                text=True,
                check=False,  # Don't fail if access denied
            )
            
            if frag_result.returncode == 0:
                # Count extents (fragmentation level)
                extents = 0
                for line in frag_result.stdout.splitlines():
                    if "VCN:" in line or "LCN:" in line:
                        extents += 1
                
                # Number of fragments is approximately extents / 2
                mft_fragments = max(1, extents // 2)
            else:
                # If we can't get fragmentation, assume 1 (unfragmented)
                mft_fragments = 1
        
        except Exception:
            # Fragmentation query failed, assume unfragmented
            mft_fragments = 1
        
        return MFTInfo(
            drive=drive,
            mft_size_bytes=mft_size,
            mft_fragments=mft_fragments,
            total_files=total_files,
            total_folders=total_folders,
        )
    
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        if "Access is denied" in error_msg or e.returncode == 5:
            raise RuntimeError(
                f"MFT analysis requires administrator privileges. "
                f"Please run from an elevated command prompt/PowerShell."
            )
        raise RuntimeError(f"Failed to get MFT info for {drive}: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Error getting MFT info for {drive}: {e}")


def analyze_mft_health(mft_info: MFTInfo) -> dict[str, any]:
    """
    Analyze MFT health and return assessment.
    
    Args:
        mft_info: MFT information
    
    Returns:
        Dictionary with health assessment
    """
    # Thresholds from spec
    SIZE_WARNING_GB = 2.0
    SIZE_CRITICAL_GB = 2.5
    FRAG_WARNING = 5
    FRAG_CRITICAL = 10
    
    mft_size_gb = mft_info.mft_size_bytes / (1024**3)
    
    # Determine size severity
    if mft_size_gb >= SIZE_CRITICAL_GB:
        size_severity = "critical"
    elif mft_size_gb >= SIZE_WARNING_GB:
        size_severity = "warning"
    else:
        size_severity = "good"
    
    # Determine fragmentation severity
    if mft_info.mft_fragments >= FRAG_CRITICAL:
        frag_severity = "critical"
    elif mft_info.mft_fragments >= FRAG_WARNING:
        frag_severity = "warning"
    else:
        frag_severity = "good"
    
    # Overall severity (worst of the two)
    if size_severity == "critical" or frag_severity == "critical":
        overall_severity = "critical"
    elif size_severity == "warning" or frag_severity == "warning":
        overall_severity = "warning"
    else:
        overall_severity = "good"
    
    return {
        "drive": mft_info.drive,
        "mft_size_bytes": mft_info.mft_size_bytes,
        "mft_size_gb": round(mft_size_gb, 2),
        "mft_fragments": mft_info.mft_fragments,
        "total_files": mft_info.total_files,
        "total_folders": mft_info.total_folders,
        "size_severity": size_severity,
        "fragmentation_severity": frag_severity,
        "overall_severity": overall_severity,
    }
