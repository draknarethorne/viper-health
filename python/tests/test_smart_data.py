"""Tests for the SMART / drive health collector."""

import json
from unittest.mock import patch

from viper_health.collectors import smart_data
from viper_health.collectors.smart_data import (
    _assess_severity,
    get_drive_health,
    is_elevated,
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


def test_assess_severity_error_counters_override_healthy_summary():
    assert _assess_severity("Healthy", 40.0, 5.0, 13, 0) == "critical"
    assert _assess_severity("Healthy", 40.0, 5.0, 1, 0) == "warning"


def test_assess_severity_latency_overrides_healthy_summary():
    assert _assess_severity("Healthy", 40.0, 5.0, 0, 0, 9_000, 4_000) == "critical"


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
        "ReadLatencyMax": 25,
        "WriteLatencyMax": 35,
        "FlushLatencyMax": 45,
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
    assert drive.read_latency_max_ms == 25.0
    assert drive.write_latency_max_ms == 35.0
    assert drive.flush_latency_max_ms == 45.0
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


def test_get_drive_health_parses_bus_type_and_reliability_available():
    disk_json = json.dumps({
        "DeviceId": "0",
        "FriendlyName": "NVMe SSD",
        "MediaType": 4,
        "BusType": "NVMe",
        "HealthStatus": "Healthy",
    })
    rel_json = json.dumps({
        "DeviceId": "0",
        "Temperature": 40,
        "Wear": 3,
        "PowerOnHours": 500,
    })

    def fake_ps(script: str):
        if "ForEach-Object" in script:
            return rel_json
        return disk_json

    with patch.object(smart_data, "_run_powershell", side_effect=fake_ps):
        result = get_drive_health()

    assert result[0].bus_type == "NVMe"
    assert result[0].reliability_available is True


def test_get_drive_health_reliability_unavailable_behind_raid():
    """RAID/VMD drive with null reliability counters (non-admin scenario)."""
    disk_json = json.dumps({
        "DeviceId": "0",
        "FriendlyName": "SAMSUNG MZVLB1T0HALR-000L2",
        "MediaType": 4,
        "BusType": "RAID",
        "HealthStatus": "Healthy",
    })
    rel_json = json.dumps({
        "DeviceId": "0",
        "Temperature": None,
        "Wear": None,
        "PowerOnHours": None,
    })

    def fake_ps(script: str):
        if "ForEach-Object" in script:
            return rel_json
        return disk_json

    with patch.object(smart_data, "_run_powershell", side_effect=fake_ps):
        result = get_drive_health()

    drive = result[0]
    assert drive.bus_type == "RAID"
    assert drive.reliability_available is False
    # Health status alone still classifies the drive.
    assert drive.severity == "good"
    assert drive.bus_type.lower() in smart_data.LIMITED_PASSTHROUGH_BUSES


def test_is_elevated_returns_bool_or_none():
    # Must never raise; returns True/False on Windows, None elsewhere.
    assert is_elevated() in (True, False, None)

