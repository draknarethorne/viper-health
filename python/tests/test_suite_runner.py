"""Tests for suite runner CLI and preset loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from viper_health.cli.suite import expand_env_path, load_presets, run_preset_scan


def test_expand_env_path_with_userprofile(monkeypatch):
    """Test environment variable expansion."""
    monkeypatch.setenv("USERPROFILE", "C:/Users/TestUser")
    result = expand_env_path("%USERPROFILE%/Documents")
    assert str(result).endswith("Documents")


def test_expand_env_path_with_wildcards():
    """Test that wildcard patterns are preserved."""
    result = expand_env_path("C:/Test/*/extensions")
    assert "*" in str(result)


def test_load_presets_default_config():
    """Test loading presets from default config file."""
    config = load_presets()

    assert "presets" in config
    assert "defaults" in config
    assert "full-system" in config["presets"]
    assert "quick-check" in config["presets"]
    assert "user-data" in config["presets"]
    assert "workspace" in config["presets"]

    # Check structure of a preset
    full_system = config["presets"]["full-system"]
    assert "description" in full_system
    assert "targets" in full_system
    assert isinstance(full_system["targets"], list)


def test_load_presets_custom_config(tmp_path):
    """Test loading custom preset config."""
    custom_config = tmp_path / "custom-presets.yaml"
    custom_config.write_text(
        """
presets:
  test-preset:
    description: "Test preset"
    targets:
      - "C:/Test"
    tiny_file_warning: 1000
defaults:
  tiny_file_max_bytes: 4096
"""
    )

    config = load_presets(custom_config)

    assert "test-preset" in config["presets"]
    assert config["presets"]["test-preset"]["tiny_file_warning"] == 1000
    assert config["defaults"]["tiny_file_max_bytes"] == 4096


def test_load_presets_missing_file():
    """Test error when config file doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Preset configuration not found"):
        load_presets(Path("nonexistent.yaml"))


def test_run_preset_scan_workspace(tmp_path):
    """Test running workspace preset scan."""
    # Create test workspace structure
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()

    # Create some test files
    for i in range(100):
        (test_dir / f"small_file_{i}.txt").write_text("x")

    # Create custom config with test preset
    config_file = tmp_path / "test-presets.yaml"
    config_file.write_text(
        f"""
presets:
  test-workspace:
    description: "Test workspace scan"
    targets:
      - "{str(test_dir).replace(chr(92), '/')}"
    tiny_file_warning: 1000
    tiny_file_critical: 2000

defaults:
  tiny_file_max_bytes: 4096
"""
    )

    # Run preset scan
    result = run_preset_scan(
        preset_name="test-workspace",
        console_summary=False,
        config_path=config_file,
    )

    assert result["preset"] == "test-workspace"
    assert result["targets_scanned"] == 1
    assert result["targets_total"] == 1
    assert len(result["scans"]) == 1
    assert result["scans"][0]["inventory"].total_files == 100


def test_run_preset_scan_invalid_preset(tmp_path):
    """Test error when preset doesn't exist."""
    config_file = tmp_path / "test-presets.yaml"
    config_file.write_text(
        """
presets:
  valid-preset:
    description: "Valid"
    targets: ["."]
defaults:
  tiny_file_max_bytes: 4096
"""
    )

    with pytest.raises(ValueError, match="Unknown preset.*nonexistent"):
        run_preset_scan(
            preset_name="nonexistent",
            config_path=config_file,
        )


def test_run_preset_scan_with_output_dir(tmp_path):
    """Test preset scan with output directory."""
    test_dir = tmp_path / "scan_target"
    test_dir.mkdir()
    (test_dir / "test.txt").write_text("test")

    output_dir = tmp_path / "reports"

    config_file = tmp_path / "test-presets.yaml"
    config_file.write_text(
        f"""
presets:
  test-preset:
    description: "Test"
    targets:
      - "{str(test_dir).replace(chr(92), '/')}"
defaults:
  tiny_file_max_bytes: 4096
"""
    )

    run_preset_scan(
        preset_name="test-preset",
        output_dir=output_dir,
        console_summary=False,
        config_path=config_file,
    )

    # Check that output files were created
    assert output_dir.exists()
    json_files = list(output_dir.glob("viper-health_test-preset_*.json"))
    assert len(json_files) == 1

    # Verify JSON structure
    report_data = json.loads(json_files[0].read_text())
    assert report_data["preset"] == "test-preset"
    assert report_data["targets_scanned"] == 1
