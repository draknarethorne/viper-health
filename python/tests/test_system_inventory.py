"""Tests for passive hardware and firmware inventory collection."""

from unittest.mock import patch

from viper_health.collectors.system_inventory import collect_system_inventory
from viper_health.utils.windows_powershell import PowerShellJsonResult


@patch("viper_health.collectors.system_inventory.run_powershell_json")
def test_collect_system_inventory_preserves_sections(mock_run):
    mock_run.return_value = PowerShellJsonResult(
        available=True,
        data={
            "Available": True,
            "CollectedAtUtc": "2026-07-25T12:00:00Z",
            "ComputerSystem": {"Manufacturer": "Example", "Model": "Board"},
            "OperatingSystem": {"BuildNumber": "26100"},
            "Cpu": [{"Name": "CPU", "Cores": 8}],
            "MemoryModules": [{"CapacityBytes": 16 * 1024**3}],
            "Gpus": [{"Name": "GPU"}],
            "Error": None,
        },
    )

    inventory = collect_system_inventory()
    payload = inventory.to_dict()

    assert inventory.available is True
    assert inventory.collected_at_utc == "2026-07-25T12:00:00Z"
    assert payload["ComputerSystem"]["Manufacturer"] == "Example"
    assert payload["Cpu"][0]["Cores"] == 8
    assert payload["error"] is None


@patch("viper_health.collectors.system_inventory.run_powershell_json")
def test_collect_system_inventory_preserves_script_error(mock_run):
    mock_run.return_value = PowerShellJsonResult(
        available=True,
        data={
            "Available": False,
            "CollectedAtUtc": "2026-07-25T12:00:00Z",
            "Error": "CIM access denied",
        },
    )

    inventory = collect_system_inventory()

    assert inventory.available is False
    assert inventory.data == {}
    assert inventory.error == "CIM access denied"


@patch("viper_health.collectors.system_inventory.run_powershell_json")
def test_collect_system_inventory_handles_runner_failure(mock_run):
    mock_run.return_value = PowerShellJsonResult(
        available=False,
        error="PowerShell not found",
    )

    inventory = collect_system_inventory()

    assert inventory.available is False
    assert inventory.error == "PowerShell not found"
