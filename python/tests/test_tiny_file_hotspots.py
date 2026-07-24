from pathlib import Path

from viper_health.analyzers.tiny_file_hotspots import analyze_tiny_file_hotspots
from viper_health.collectors.file_inventory import scan_file_inventory


def _write_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_analyzer_flags_warning_and_critical(tmp_path: Path) -> None:
    warn_dir = tmp_path / "warn"
    crit_dir = tmp_path / "crit"

    for i in range(3):
        _write_file(warn_dir / f"w-{i}.bin", 100)
    for i in range(5):
        _write_file(crit_dir / f"c-{i}.bin", 100)

    inventory = scan_file_inventory(tmp_path, tiny_file_max_bytes=4096)
    report = analyze_tiny_file_hotspots(
        inventory,
        warning_threshold=3,
        critical_threshold=5,
    )

    findings = {f.path: f for f in report.hotspots}

    assert findings[str(warn_dir.resolve())].severity == "warning"
    assert findings[str(crit_dir.resolve())].severity == "critical"


def test_analyzer_suppresses_safe_path(tmp_path: Path) -> None:
    safe_dir = tmp_path / "safe-zone"
    for i in range(4):
        _write_file(safe_dir / f"f-{i}.bin", 100)

    inventory = scan_file_inventory(tmp_path, tiny_file_max_bytes=4096)
    report = analyze_tiny_file_hotspots(
        inventory,
        warning_threshold=2,
        critical_threshold=5,
        safe_paths=[str(safe_dir)],
    )

    finding = next(f for f in report.hotspots if f.path == str(safe_dir.resolve()))
    assert finding.suppressed is True
    assert finding.reason == "safe_path"
