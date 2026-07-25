"""Tests for the safety-gated benchmark CLI."""

import json
from unittest.mock import patch

from viper_health.analyzers.benchmark_preflight import BenchmarkPreflight
from viper_health.cli.benchmark_io import main


@patch("viper_health.cli.benchmark_io.run_io_benchmark")
@patch("viper_health.cli.benchmark_io.run_benchmark_preflight")
def test_cli_blocks_before_benchmark_files_are_created(
    mock_preflight,
    mock_benchmark,
    tmp_path,
):
    mock_preflight.return_value = BenchmarkPreflight(
        False,
        30,
        ("storage: 2 relevant event(s) (critical)",),
        "critical",
        2,
        1,
        (),
    )
    output = tmp_path / "blocked.json"

    exit_code = main(["--output", str(output)])

    assert exit_code == 2
    mock_benchmark.assert_not_called()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["preflight"]["allowed"] is False
    assert payload["results"] == []


@patch("viper_health.cli.benchmark_io.run_io_benchmark", return_value=[])
@patch("viper_health.cli.benchmark_io.run_benchmark_preflight")
def test_cli_runs_only_after_clean_preflight(mock_preflight, mock_benchmark):
    mock_preflight.return_value = BenchmarkPreflight(
        True,
        30,
        (),
        "info",
        0,
        1,
        (),
    )

    exit_code = main([])

    assert exit_code == 0
    mock_benchmark.assert_called_once()
