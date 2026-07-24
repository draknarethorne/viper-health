from pathlib import Path

from viper_health.cli.scan_tiny_files import build_tiny_file_report
from viper_health.collectors.file_inventory import scan_file_inventory


def _write_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_build_tiny_file_report_contains_summary_and_hotspots(tmp_path: Path) -> None:
    hotspot = tmp_path / "hotspot"
    for i in range(3):
        _write_file(hotspot / f"{i}.bin", 100)

    inventory = scan_file_inventory(tmp_path, tiny_file_max_bytes=4096)
    report = build_tiny_file_report(
        inventory,
        warning_threshold=2,
        critical_threshold=5,
        safe_paths=[],
    )

    assert report["summary"]["total_files"] == 3
    assert report["summary"]["tiny_files"] == 3
    assert report["summary"]["hotspot_count"] == 1
    assert report["summary"]["active_hotspot_count"] == 1
    assert report["hotspots"][0]["path"] == str(hotspot.resolve())
