"""Tests for comprehensive system-health report orchestration."""

import json
from unittest.mock import patch

from viper_health.cli.system_report import _collect, build_system_health_report, main
from viper_health.collectors.system_inventory import SystemInventory
from viper_health.collectors.windows_events import EventLogSnapshot, WindowsEvent


def _inventory():
    return SystemInventory(
        available=True,
        collected_at_utc="2026-07-25T12:00:00Z",
        data={
            "ComputerSystem": {
                "Manufacturer": "Example",
                "Model": "Machine",
                "TotalPhysicalMemoryBytes": 16 * 1024**3,
            },
            "OperatingSystem": {"Caption": "Windows", "BuildNumber": "26100"},
            "Cpu": [{"Name": "CPU", "Cores": 6, "LogicalProcessors": 12}],
            "MemoryModules": [{"CapacityBytes": 16 * 1024**3}],
            "Gpus": [{"Name": "GPU"}],
            "SecureBootEnabled": False,
        },
    )


def _snapshot(*events):
    return EventLogSnapshot(
        available=True,
        lookback_days=90,
        query_start_utc="2026-04-01T00:00:00Z",
        collected_at_utc="2026-07-25T12:00:00Z",
        log_oldest_utc="2026-03-01T00:00:00Z",
        log_newest_utc="2026-07-25T12:00:00Z",
        log_record_count=100,
        events=events,
    )


@patch("viper_health.cli.system_report.collect_system_events")
@patch("viper_health.cli.system_report.collect_system_inventory")
def test_build_report_is_serializable_and_marks_storage_fault_critical(
    mock_inventory,
    mock_events,
):
    mock_inventory.return_value = _inventory()
    mock_events.return_value = _snapshot(
        WindowsEvent(
            record_id=1,
            timestamp_utc="2026-07-01T00:00:00Z",
            provider="storahci",
            event_id=129,
            level="Warning",
            message="Reset issued",
            properties=("RaidPort0",),
        ),
        WindowsEvent(
            record_id=2,
            timestamp_utc="2026-07-02T00:00:00Z",
            provider="disk",
            event_id=153,
            level="Warning",
            message="I/O retried",
            properties=("Disk 0",),
        ),
    )

    report = build_system_health_report(include_storage=False)

    assert report["schema_version"] == 1
    assert report["assessment"]["severity"] == "critical"
    assert report["event_analysis"]["domain_event_counts"]["storage"] == 2
    assert "benchmark" in report["recommendations"][-1].lower()
    json.dumps(report)


@patch("viper_health.cli.system_report.collect_system_events")
@patch("viper_health.cli.system_report.collect_system_inventory")
def test_build_report_does_not_claim_good_when_all_sections_skipped(
    mock_inventory,
    mock_events,
):
    report = build_system_health_report(
        include_inventory=False,
        include_events=False,
        include_storage=False,
    )

    assert report["assessment"]["severity"] == "unknown"
    assert report["assessment"]["confidence"] == "low"
    mock_inventory.assert_not_called()
    mock_events.assert_not_called()


def test_collect_marks_empty_critical_section_unavailable():
    value, status = _collect(
        "physical_drives",
        lambda: [],
        empty_is_unavailable=True,
    )

    assert value == []
    assert status == {
        "available": False,
        "error": "physical_drives returned no records",
    }


@patch("viper_health.cli.system_report.collect_system_events")
@patch("viper_health.cli.system_report.collect_system_inventory")
def test_main_writes_json_and_markdown(mock_inventory, mock_events, tmp_path):
    mock_inventory.return_value = _inventory()
    mock_events.return_value = _snapshot()
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"

    exit_code = main(
        [
            "--no-storage",
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(json_path.read_text(encoding="utf-8"))["report_type"] == "comprehensive_system_health"
    markdown = md_path.read_text(encoding="utf-8")
    assert "# Viper Health Comprehensive System Report" in markdown
    assert "**Secure Boot:** False" in markdown
    assert "No benchmarks or mutating operations" not in markdown
    assert "## AI review guidance" in markdown
