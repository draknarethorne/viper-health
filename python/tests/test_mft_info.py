"""Tests for MFT (Master File Table) analysis."""

from unittest.mock import Mock, patch

import pytest

from viper_health.collectors.mft_info import (
    MFTInfo,
    _parse_fsutil_size,
    analyze_mft_health,
    get_mft_info,
)


def test_mft_info_dataclass():
    """Test MFTInfo dataclass creation."""
    mft = MFTInfo(
        drive="C:",
        mft_size_bytes=1024*1024*1024,  # 1 GB
        mft_fragments=3,
        total_files=100000,
        total_folders=10000,
    )
    
    assert mft.drive == "C:"
    assert mft.mft_size_bytes == 1024*1024*1024
    assert mft.mft_fragments == 3
    assert mft.total_files == 100000


def test_analyze_mft_health_good():
    """Test MFT health analysis with good metrics."""
    mft = MFTInfo(
        drive="C:",
        mft_size_bytes=1024*1024*1024,  # 1 GB (< 2 GB threshold)
        mft_fragments=2,  # < 5 fragments
        total_files=100000,
        total_folders=10000,
    )
    
    analysis = analyze_mft_health(mft)
    
    assert analysis["drive"] == "C:"
    assert analysis["mft_size_gb"] == 1.0
    assert analysis["mft_fragments"] == 2
    assert analysis["size_severity"] == "good"
    assert analysis["fragmentation_severity"] == "good"
    assert analysis["overall_severity"] == "good"


def test_analyze_mft_health_warning_size():
    """Test MFT health analysis with warning size."""
    mft = MFTInfo(
        drive="C:",
        mft_size_bytes=int(2.3 * 1024**3),  # 2.3 GB (warning threshold)
        mft_fragments=2,
        total_files=500000,
        total_folders=50000,
    )
    
    analysis = analyze_mft_health(mft)
    
    assert analysis["size_severity"] == "warning"
    assert analysis["fragmentation_severity"] == "good"
    assert analysis["overall_severity"] == "warning"


def test_analyze_mft_health_critical_fragmentation():
    """Test MFT health analysis with critical fragmentation."""
    mft = MFTInfo(
        drive="D:",
        mft_size_bytes=1024*1024*1024,  # 1 GB
        mft_fragments=15,  # > 10 fragments (critical)
        total_files=100000,
        total_folders=10000,
    )
    
    analysis = analyze_mft_health(mft)
    
    assert analysis["size_severity"] == "good"
    assert analysis["fragmentation_severity"] == "critical"
    assert analysis["overall_severity"] == "critical"


def test_analyze_mft_health_critical_both():
    """Test MFT health analysis with both metrics critical."""
    mft = MFTInfo(
        drive="C:",
        mft_size_bytes=int(3.0 * 1024**3),  # 3 GB (critical)
        mft_fragments=12,  # > 10 (critical)
        total_files=1000000,
        total_folders=100000,
    )
    
    analysis = analyze_mft_health(mft)
    
    assert analysis["size_severity"] == "critical"
    assert analysis["fragmentation_severity"] == "critical"
    assert analysis["overall_severity"] == "critical"


def test_get_mft_info_invalid_drive():
    """Test get_mft_info with invalid drive format."""
    with pytest.raises(ValueError, match="Drive must end with colon"):
        get_mft_info("C")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0x0000000040000000", 1024**3),
        ("1.45 GB", int(1.45 * 1024**3)),
        ("200.13 MB", int(200.13 * 1024**2)),
        ("1,024 KB", 1024 * 1024),
    ],
)
def test_parse_fsutil_size_formats(value, expected):
    """Modern and legacy fsutil size formats both parse to bytes."""
    assert _parse_fsutil_size(value) == expected


@patch("subprocess.run")
def test_get_mft_info_success(mock_run):
    """Test get_mft_info with successful fsutil output."""
    # Mock fsutil ntfsinfo output
    mock_ntfsinfo = Mock()
    mock_ntfsinfo.returncode = 0
    mock_ntfsinfo.stdout = """
NTFS Volume Serial Number:       0x1234567890abcdef
NTFS Version:                    3.1
LFS Version:                     2.0
Total Sectors:                   0x000000001dcd6500
Total Clusters:                  0x0000000003b9aca0
Free Clusters:                   0x0000000001234567
Total Reserved Clusters:         0x0000000000000000
Bytes Per Sector:                512
Bytes Per Physical Sector:       4096
Bytes Per Cluster:               4096
Bytes Per FileRecord Segment:    1024
Clusters Per FileRecord Segment: 0
Mft Valid Data Length:           0x0000000040000000
Mft Start Lcn:                   0x00000000000c0000
Mft2 Start Lcn:                  0x0000000000000002
Mft Zone Start:                  0x00000000008e3d60
Mft Zone End:                    0x0000000000904640
File Records:                    524288
Folders:                         45678
"""
    
    # Mock fragmentation query (will fail, defaults to 1)
    mock_frag = Mock()
    mock_frag.returncode = 5  # Access denied
    mock_frag.stdout = ""
    
    # Configure mock to return different results for different calls
    mock_run.side_effect = [mock_ntfsinfo, mock_frag]
    
    mft = get_mft_info("C:")
    
    assert mft.drive == "C:"
    assert mft.mft_size_bytes == 0x40000000  # 1 GB
    assert mft.mft_fragments == 1  # Fallback
    assert mft.total_files == 524288
    assert mft.total_folders == 45678


@patch("subprocess.run")
def test_get_mft_info_modern_human_readable_size(mock_run):
    """Modern Windows emits MFT sizes as human-readable values."""
    mock_ntfsinfo = Mock()
    mock_ntfsinfo.returncode = 0
    mock_ntfsinfo.stdout = """
Mft Valid Data Length :            1.45 GB
MFT Zone Size  :                   200.13 MB
"""

    mock_frag = Mock()
    mock_frag.returncode = 5
    mock_frag.stdout = ""
    mock_run.side_effect = [mock_ntfsinfo, mock_frag]

    mft = get_mft_info("C:")

    assert mft.mft_size_bytes == int(1.45 * 1024**3)
    assert mft.mft_fragments == 1


@patch("subprocess.run")
def test_get_mft_info_command_failure(mock_run):
    """Test get_mft_info when fsutil command fails."""
    mock_run.side_effect = Exception("Command failed")
    
    with pytest.raises(RuntimeError, match="Error getting MFT info"):
        get_mft_info("C:")
