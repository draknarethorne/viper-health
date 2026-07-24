"""Tests for the SMART / drive health collector."""

import json
from unittest.mock import patch

from viper_health.collectors import smart_data
from viper_health.collectors.smart_data import (
    _assess_severity,
    get_drive_health,
)


def test_assess_severity_healthy_cool():
    assert _assess_severity("Healthy", 40.0, 10.0) == "good"


def test_assess_severity_hot_critical():
    assert _assess_severity("Healthy", 75.0, 10.0) == "critical"


def test_assess_severity_warm_warning():
    assert _assess_severity("Healthy", 60.0, 10.0) == "warning"


def test_assess_severity_high_wear():
    assert _assess_severity("Healthy", 40.0, 95.0) == "critical"


def test_assess_severity_unhealthy_status():
    assert _assess_severity("Unhealthy", None, None) == "critical"


def test_assess_severity_unknown():
    assert _assess_severity("Unknown", None, None) == "unknown"


def test_get_drive_health_no_data():
    # Both PowerShell calls return None -> no disks
    with patch.object(smart_data, "_run_powershell", return_value=None):
        result = get_drive_health()
    assert result == []


def test_get_drive_health_parses_disks():
    disk_json = json.dumps({
        "DeviceId": "0",
        "FriendlyName": "Test SSD",
        "MediaType": 4,
        "HealthStatus": "Healthy",
    })
    rel_json = json.dumps({
        "DeviceId": "0",
        "Temperature": 45,
        "Wear": 5,
        "PowerOnHours": 1000,
        "ReadErrorsTotal": 0,
        "WriteErrorsTotal": 0,
    })

    def fake_ps(script: str):
        if "Get-StorageReliabilityCounter" in script and "ForEach-Object" in script:
            return rel_json
        return disk_json

    with patch.object(smart_data, "_run_powershell", side_effect=fake_ps):
        result = get_drive_health()

    assert len(result) == 1
    drive = result[0]
    assert drive.friendly_name == "Test SSD"
    assert drive.media_type == "SSD"
    assert drive.temperature_c == 45.0
    assert drive.wear_percent == 5.0
    assert drive.power_on_hours == 1000
    assert drive.severity == "good"


def test_get_drive_health_hot_drive_critical():
    disk_json = json.dumps({
        "DeviceId": "0",
        "FriendlyName": "Hot SSD",
        "MediaType": 4,
        "HealthStatus": "Healthy",
    })
    rel_json = json.dumps({
        "DeviceId": "0",
        "Temperature": 80,
        "Wear": 5,
    })

    def fake_ps(script: str):
        if "ForEach-Object" in script:
            return rel_json
        return disk_json

    with patch.object(smart_data, "_run_powershell", side_effect=fake_ps):
        result = get_drive_health()

    assert result[0].severity == "critical"
