"""Tests for the top disk-I/O process collector."""

import json
from unittest.mock import patch

from viper_health.collectors import io_processes
from viper_health.collectors.io_processes import get_top_io_processes


def test_no_data_returns_empty():
    with patch.object(io_processes, "_run_powershell", return_value=None):
        assert get_top_io_processes() == []


def test_parses_process_list():
    payload = json.dumps([
        {"Name": "searchindexer", "Bytes": 5_000_000},
        {"Name": "chrome", "Bytes": 1_000_000},
    ])
    with patch.object(io_processes, "_run_powershell", return_value=payload):
        result = get_top_io_processes()

    assert len(result) == 2
    assert result[0].name == "searchindexer"
    assert result[0].io_mb_per_sec == round(5_000_000 / (1024 * 1024), 3)


def test_parses_single_object():
    payload = json.dumps({"Name": "msmpeng", "Bytes": 2_000_000})
    with patch.object(io_processes, "_run_powershell", return_value=payload):
        result = get_top_io_processes()

    assert len(result) == 1
    assert result[0].name == "msmpeng"


def test_handles_invalid_json():
    with patch.object(io_processes, "_run_powershell", return_value="not json"):
        assert get_top_io_processes() == []


def test_handles_missing_bytes_field():
    payload = json.dumps([{"Name": "proc"}])
    with patch.object(io_processes, "_run_powershell", return_value=payload):
        result = get_top_io_processes()
    assert result[0].io_bytes_per_sec == 0.0
