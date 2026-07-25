"""Tests for passive Windows event collection."""

from unittest.mock import patch

import pytest

from viper_health.collectors.windows_events import collect_system_events
from viper_health.utils.windows_powershell import PowerShellJsonResult


@patch("viper_health.collectors.windows_events.run_powershell_json")
def test_collect_system_events_parses_single_event(mock_run):
    mock_run.return_value = PowerShellJsonResult(
        available=True,
        data={
            "Available": True,
            "QueryStartUtc": "2026-04-01T00:00:00Z",
            "CollectedAtUtc": "2026-07-01T00:00:00Z",
            "LogOldestUtc": "2026-03-01T00:00:00Z",
            "LogNewestUtc": "2026-07-01T00:00:00Z",
            "LogRecordCount": 1000,
            "Events": {
                "RecordId": 42,
                "TimestampUtc": "2026-06-01T00:00:00Z",
                "Provider": "storahci",
                "EventId": 129,
                "Level": "Warning",
                "Message": "Reset to device",
                "Properties": "RaidPort0",
            },
            "Error": None,
        },
    )

    snapshot = collect_system_events(lookback_days=90)

    assert snapshot.available is True
    assert snapshot.log_record_count == 1000
    assert len(snapshot.events) == 1
    assert snapshot.events[0].event_id == 129
    assert snapshot.events[0].properties == ("RaidPort0",)
    assert snapshot.to_dict()["event_count"] == 1


@patch("viper_health.collectors.windows_events.run_powershell_json")
def test_collect_system_events_preserves_unavailable_state(mock_run):
    mock_run.return_value = PowerShellJsonResult(
        available=False,
        error="PowerShell unavailable",
    )

    snapshot = collect_system_events()

    assert snapshot.available is False
    assert snapshot.events == ()
    assert snapshot.error == "PowerShell unavailable"


def test_collect_system_events_rejects_invalid_window():
    with pytest.raises(ValueError, match="at least 1"):
        collect_system_events(lookback_days=0)
