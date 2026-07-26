"""Tests for the cross-machine profiles index generator."""

import json

from viper_health.cli.profiles_index import (
    build_index_markdown,
    collect_machine_rows,
    main,
    write_latest_pointers,
)


def _write_report(host_dir, stamp, *, host, severity="good", capability="solid"):
    host_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "host": host,
        "timestamp_utc": f"2026-07-{stamp}T12:00:00+00:00",
        "assessment": {"severity": severity, "confidence": "high"},
        "capability": {"tier": capability},
        "system_inventory": {
            "available": True,
            "ComputerSystem": {
                "Manufacturer": "ACME",
                "Model": "Tower",
                "TotalPhysicalMemoryBytes": 32 * 1024**3,
            },
            "OperatingSystem": {"Caption": "Microsoft Windows 11 Pro"},
            "Cpu": [{"Name": "AMD Ryzen 7 5800X"}],
        },
        "storage": {
            "drives": [
                {"friendly_name": "Samsung SSD", "bus_type": "NVMe", "wear_percent": 0.0, "severity": "good"}
            ],
            "disk_space": {"free_percent": 42.5},
        },
    }
    path = host_dir / f"system-health-2026072{stamp}T120000Z.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    (host_dir / f"system-health-2026072{stamp}T120000Z.md").write_text("# report", encoding="utf-8")
    return path


def test_collect_machine_rows_picks_newest(tmp_path):
    host_dir = tmp_path / "DESK-1"
    _write_report(host_dir, "1", host="DESK-1", severity="warning", capability="dated")
    _write_report(host_dir, "5", host="DESK-1", severity="good", capability="solid")

    rows = collect_machine_rows(tmp_path)

    assert len(rows) == 1
    row = rows[0]
    assert row["host"] == "DESK-1"
    assert row["severity"] == "GOOD"  # newest report wins
    assert row["capability"] == "SOLID"
    assert row["ram"] == "32 GiB"
    assert row["drive"] == "Samsung SSD"
    assert row["free_percent"] == 42.5


def test_collect_machine_rows_reads_tiny_ratio_from_profile(tmp_path):
    host_dir = tmp_path / "LAP-2"
    _write_report(host_dir, "3", host="LAP-2")
    # profile_machine file lives at data/profiles/<host>.json
    (tmp_path / "LAP-2.json").write_text(json.dumps({"tiny_file_ratio": 50.6}), encoding="utf-8")

    rows = collect_machine_rows(tmp_path)

    assert rows[0]["tiny_file_ratio"] == 50.6


def test_build_index_markdown_has_rows_and_legend(tmp_path):
    _write_report(tmp_path / "DESK-1", "1", host="DESK-1")
    rows = collect_machine_rows(tmp_path)

    markdown = build_index_markdown(rows)

    assert "# Viper Health — Machine Index" in markdown
    assert "| DESK-1 |" in markdown
    assert "## Legend" in markdown


def test_build_index_markdown_has_layered_sections(tmp_path):
    host_dir = tmp_path / "DESK-1"
    _write_report(host_dir, "1", host="DESK-1")
    # profile_machine file with benchmark medians drives Layer 3.
    (tmp_path / "DESK-1.json").write_text(
        json.dumps(
            {
                "tiny_file_ratio": 5.0,
                "benchmark_results": [
                    {"test_name": "sequential_write", "throughput_mb_s": 264.0},
                    {"test_name": "sequential_read", "throughput_mb_s": 619.0},
                    {"test_name": "random_write", "throughput_mb_s": 42.0},
                    {"test_name": "random_read", "throughput_mb_s": 129.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    rows = collect_machine_rows(tmp_path)
    markdown = build_index_markdown(rows)

    assert "## Layer 1 — Overall ranking" in markdown
    assert "## Layer 2 — Per-resource spec scores" in markdown
    assert "## Layer 3 — Storage: spec vs actual" in markdown
    assert "## Layer 4 — Tuning & optimization recommendations" in markdown
    # Layer 3 should show actual/expected for the benchmarked drive.
    assert "264/1000" in markdown


def test_collect_machine_rows_gathers_benchmarks(tmp_path):
    host_dir = tmp_path / "DESK-1"
    _write_report(host_dir, "1", host="DESK-1")
    (tmp_path / "DESK-1.json").write_text(
        json.dumps(
            {
                "benchmark_results": [
                    {"test_name": "sequential_write", "throughput_mb_s": 264.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    rows = collect_machine_rows(tmp_path)
    assert rows[0]["benchmarks"]["sequential_write"] == 264.0



def test_build_index_markdown_empty(tmp_path):
    markdown = build_index_markdown([])
    assert "No machine reports found" in markdown


def test_write_latest_pointers_creates_copies(tmp_path):
    host_dir = tmp_path / "DESK-1"
    _write_report(host_dir, "1", host="DESK-1")
    _write_report(host_dir, "9", host="DESK-1", severity="critical")

    written = write_latest_pointers(tmp_path)

    latest_json = host_dir / "latest.json"
    latest_md = host_dir / "latest.md"
    assert latest_json in written
    assert latest_md in written
    # latest.json must mirror the newest report (stamp 9 → critical).
    assert json.loads(latest_json.read_text())["assessment"]["severity"] == "critical"


def test_main_writes_index(tmp_path):
    _write_report(tmp_path / "DESK-1", "1", host="DESK-1")
    output = tmp_path / "INDEX.md"

    exit_code = main(["--profiles-dir", str(tmp_path), "--output", str(output)])

    assert exit_code == 0
    assert output.exists()
    assert "| DESK-1 |" in output.read_text(encoding="utf-8")
    assert (tmp_path / "DESK-1" / "latest.json").exists()
