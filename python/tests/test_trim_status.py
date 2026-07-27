"""Tests for TRIM status checker."""

from unittest.mock import Mock, patch

import pytest

from viper_health.collectors.trim_status import TRIMStatus, check_trim_status


def test_trim_status_dataclass():
    """Test TRIMStatus dataclass creation."""
    status = TRIMStatus(
        drive="C:",
        trim_enabled=True,
        raw_value=0,
        severity="good",
    )

    assert status.drive == "C:"
    assert status.trim_enabled is True
    assert status.raw_value == 0
    assert status.severity == "good"


@patch("subprocess.run")
def test_check_trim_status_enabled(mock_run):
    """Test TRIM status when enabled."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "DisableDeleteNotify = 0\n"
    mock_run.return_value = mock_result

    status = check_trim_status("C:")

    assert status.drive == "C:"
    assert status.trim_enabled is True
    assert status.raw_value == 0
    assert status.severity == "good"


@patch("subprocess.run")
def test_check_trim_status_disabled(mock_run):
    """Test TRIM status when disabled."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "DisableDeleteNotify = 1\n"
    mock_run.return_value = mock_result

    status = check_trim_status("C:")

    assert status.drive == "C:"
    assert status.trim_enabled is False
    assert status.raw_value == 1
    assert status.severity == "critical"


@patch("subprocess.run")
def test_check_trim_status_modern_multiline(mock_run):
    """Modern fsutil output: per-filesystem lines with trailing descriptions."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = (
        "NTFS DisableDeleteNotify = 0  (Allows TRIM operations to be sent "
        "to the storage device)\n"
        "ReFS DisableDeleteNotify = 1  (Disables TRIM operations)\n"
    )
    mock_run.return_value = mock_result

    status = check_trim_status("C:")

    # NTFS line takes priority; its value 0 means TRIM enabled.
    assert status.trim_enabled is True
    assert status.raw_value == 0
    assert status.severity == "good"


@patch("subprocess.run")
def test_check_trim_status_modern_multiline_disabled(mock_run):
    """Modern fsutil output where NTFS reports TRIM disabled."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = (
        "NTFS DisableDeleteNotify = 1  (Disables TRIM operations)\n"
        "ReFS DisableDeleteNotify = 0  (Allows TRIM operations)\n"
    )
    mock_run.return_value = mock_result

    status = check_trim_status("C:")

    assert status.trim_enabled is False
    assert status.raw_value == 1
    assert status.severity == "critical"


@patch("subprocess.run")
def test_check_trim_status_access_denied(mock_run):
    """Test TRIM status with access denied."""
    mock_result = Mock()
    mock_result.returncode = 5
    mock_result.stderr = "Access is denied"
    mock_run.return_value = mock_result

    with pytest.raises(RuntimeError, match="administrator privileges"):
        check_trim_status("C:")


@patch("subprocess.run")
def test_check_trim_status_command_failure(mock_run):
    """Test TRIM status with command failure."""
    mock_run.side_effect = Exception("Command failed")

    with pytest.raises(RuntimeError, match="Error checking TRIM status"):
        check_trim_status("C:")
