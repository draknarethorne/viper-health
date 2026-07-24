"""Tests for disk space analyzer."""

from unittest.mock import Mock, patch

import pytest

from viper_health.collectors.disk_space import (
    DiskSpaceInfo,
    analyze_disk_space,
    bytes_to_gb,
    format_disk_space_summary,
)


def test_disk_space_info_dataclass():
    """Test DiskSpaceInfo dataclass creation."""
    info = DiskSpaceInfo(
        drive="C:",
        total_bytes=500_000_000_000,
        used_bytes=400_000_000_000,
        free_bytes=100_000_000_000,
        free_percent=20.0,
        severity="good",
    )
    
    assert info.drive == "C:"
    assert info.total_bytes == 500_000_000_000
    assert info.free_percent == 20.0
    assert info.severity == "good"


def test_bytes_to_gb():
    """Test bytes to GB conversion."""
    assert bytes_to_gb(1024**3) == 1.0
    assert bytes_to_gb(500 * 1024**3) == 500.0
    assert round(bytes_to_gb(1536 * 1024**2), 2) == 1.5


@patch("shutil.disk_usage")
def test_analyze_disk_space_good(mock_usage):
    """Test disk space analysis with healthy free space (>20%)."""
    mock_usage.return_value = Mock(
        total=500_000_000_000,  # 500 GB
        used=400_000_000_000,   # 400 GB
        free=100_000_000_000,   # 100 GB (20%)
    )
    
    info = analyze_disk_space("C:")
    
    assert info.drive == "C:"
    assert info.total_bytes == 500_000_000_000
    assert info.free_bytes == 100_000_000_000
    assert info.free_percent == 20.0
    assert info.severity == "good"


@patch("shutil.disk_usage")
def test_analyze_disk_space_warning(mock_usage):
    """Test disk space analysis with warning free space (10-20%)."""
    mock_usage.return_value = Mock(
        total=500_000_000_000,  # 500 GB
        used=425_000_000_000,   # 425 GB
        free=75_000_000_000,    # 75 GB (15%)
    )
    
    info = analyze_disk_space("C:")
    
    assert info.free_percent == 15.0
    assert info.severity == "warning"


@patch("shutil.disk_usage")
def test_analyze_disk_space_critical(mock_usage):
    """Test disk space analysis with critical free space (<10%)."""
    mock_usage.return_value = Mock(
        total=500_000_000_000,  # 500 GB
        used=475_000_000_000,   # 475 GB
        free=25_000_000_000,    # 25 GB (5%)
    )
    
    info = analyze_disk_space("C:")
    
    assert info.free_percent == 5.0
    assert info.severity == "critical"


@patch("shutil.disk_usage")
def test_analyze_disk_space_drive_not_found(mock_usage):
    """Test disk space analysis with non-existent drive."""
    mock_usage.side_effect = FileNotFoundError()
    
    with pytest.raises(RuntimeError, match="Drive not found"):
        analyze_disk_space("Z:")


def test_format_disk_space_summary():
    """Test disk space summary formatting."""
    info = DiskSpaceInfo(
        drive="C:",
        total_bytes=500 * 1024**3,
        used_bytes=400 * 1024**3,
        free_bytes=100 * 1024**3,
        free_percent=20.0,
        severity="good",
    )
    
    summary = format_disk_space_summary(info)
    
    assert summary["drive"] == "C:"
    assert summary["total_gb"] == 500.0
    assert summary["used_gb"] == 400.0
    assert summary["free_gb"] == 100.0
    assert summary["free_percent"] == 20.0
    assert summary["severity"] == "good"
