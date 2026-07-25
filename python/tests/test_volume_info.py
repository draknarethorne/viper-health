"""Tests for mounted-volume inventory collection."""

import json
from unittest.mock import Mock, patch

from viper_health.collectors.volume_info import get_volume_info


@patch("subprocess.run")
def test_get_volume_info_parses_and_sorts(mock_run):
    result = Mock(returncode=0)
    result.stdout = json.dumps([
        {
            "DriveLetter": "D",
            "FileSystemLabel": "Data",
            "FileSystem": "NTFS",
            "DriveType": "Fixed",
            "HealthStatus": "Healthy",
            "Size": 1_000,
            "SizeRemaining": 250,
        },
        {
            "DriveLetter": "C",
            "FileSystemLabel": "System",
            "FileSystem": "NTFS",
            "DriveType": "Fixed",
            "HealthStatus": "Healthy",
            "Size": 2_000,
            "SizeRemaining": 1_000,
        },
    ])
    mock_run.return_value = result

    volumes = get_volume_info()

    assert [volume.drive for volume in volumes] == ["C:", "D:"]
    assert volumes[0].free_percent == 50.0
    assert volumes[1].label == "Data"
    assert volumes[1].free_percent == 25.0


@patch("subprocess.run")
def test_get_volume_info_accepts_single_object(mock_run):
    result = Mock(returncode=0)
    result.stdout = json.dumps({
        "DriveLetter": "C",
        "FileSystemLabel": None,
        "FileSystem": "ReFS",
        "DriveType": "Fixed",
        "HealthStatus": "Healthy",
        "Size": 100,
        "SizeRemaining": 20,
    })
    mock_run.return_value = result

    volumes = get_volume_info()

    assert len(volumes) == 1
    assert volumes[0].filesystem == "ReFS"
    assert volumes[0].label == ""


@patch("subprocess.run")
def test_get_volume_info_degrades_gracefully(mock_run):
    mock_run.side_effect = FileNotFoundError("powershell unavailable")

    assert get_volume_info() == []


@patch("subprocess.run")
def test_get_volume_info_skips_invalid_records(mock_run):
    result = Mock(returncode=0)
    result.stdout = json.dumps([
        {"DriveLetter": None, "Size": 100, "SizeRemaining": 20},
        {"DriveLetter": "C", "Size": "not-a-number", "SizeRemaining": 20},
    ])
    mock_run.return_value = result

    assert get_volume_info() == []
