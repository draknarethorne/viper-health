"""Tests for safe PowerShell JSON execution."""

import json
import subprocess
from unittest.mock import Mock, patch

from viper_health.utils.windows_powershell import run_powershell_json


@patch("subprocess.run")
def test_run_powershell_json_decodes_payload(mock_run):
    mock_run.return_value = Mock(
        returncode=0,
        stdout="\ufeff" + json.dumps({"ok": True}),
        stderr="",
    )

    result = run_powershell_json("Get-Thing")

    assert result.available is True
    assert result.data == {"ok": True}
    assert mock_run.call_args.args[0][:3] == [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
    ]


@patch("subprocess.run")
def test_run_powershell_json_reports_nonzero_exit(mock_run):
    mock_run.return_value = Mock(returncode=5, stdout="", stderr="Access denied")

    result = run_powershell_json("Get-Thing")

    assert result.available is False
    assert result.error == "Access denied"


@patch("subprocess.run")
def test_run_powershell_json_reports_invalid_json(mock_run):
    mock_run.return_value = Mock(returncode=0, stdout="not-json", stderr="")

    result = run_powershell_json("Get-Thing")

    assert result.available is False
    assert "invalid JSON" in result.error


@patch("subprocess.run")
def test_run_powershell_json_reports_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=2)

    result = run_powershell_json("Get-Thing", timeout_seconds=2)

    assert result.available is False
    assert "timed out" in result.error
