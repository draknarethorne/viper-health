"""Tests for startup/background-load analysis."""

from viper_health.analyzers.startup_load import _exe_token, analyze_startup


def test_exe_token_extracts_basename():
    assert _exe_token('"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --flag') == "chrome"
    assert _exe_token("C:\\Windows\\System32\\OneDrive.exe /background") == "onedrive"


def test_analyze_flags_known_startup_and_services():
    data = {
        "StartupCommands": [
            {"Name": "OneDrive", "Command": "C:\\...\\OneDrive.exe /background", "Location": "HKCU\\...\\Run"},
            {"Name": "Discord", "Command": '"C:\\...\\Discord.exe"', "Location": "Startup"},
            {"Name": "MysteryTool", "Command": "mystery.exe", "Location": "HKLM\\...\\Run"},
        ],
        "Services": [
            {"Name": "gupdate", "DisplayName": "Google Update Service", "State": "Running", "StartMode": "Auto"},
            {"Name": "wuauserv", "DisplayName": "Windows Update", "State": "Running", "StartMode": "Auto"},
        ],
        "Processes": [
            {"Name": "chrome", "Count": 12, "WorkingSetBytes": 2_000_000_000},
            {"Name": "Code", "Count": 6, "WorkingSetBytes": 900_000_000},
            {"Name": "svchost", "Count": 80, "WorkingSetBytes": 3_000_000_000},
        ],
    }

    result = analyze_startup(data)

    known = [e for e in result["startup_entries"] if e["known"]]
    labels = {e["label"] for e in known}
    assert "OneDrive" in labels
    assert "Discord" in labels

    # Google updater is a Manual candidate; Windows Update is protected.
    candidate_names = {c["name"] for c in result["manual_service_candidates"]}
    assert "gupdate" in candidate_names
    assert "wuauserv" not in candidate_names

    # Known heavy apps are surfaced; unknown svchost is not.
    heavy_labels = {p["label"] for p in result["heavy_processes"]}
    assert "Google Chrome" in heavy_labels
    assert "VS Code" in heavy_labels
    assert all("svchost" not in p["name"].lower() for p in result["heavy_processes"])

    assert result["recommendations"]


def test_analyze_empty_data_is_safe():
    result = analyze_startup({})
    assert result["startup_entries"] == []
    assert result["manual_service_candidates"] == []
    assert result["heavy_processes"] == []
    assert result["recommendations"]
