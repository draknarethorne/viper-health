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

    assert len(report.findings) == 2
    assert report.warning_count == 1
    assert report.critical_count == 1

    # Check severity assignment
    findings_dict = {f.path: f for f in report.findings}
    assert findings_dict[warn_dir].severity == "warning"
    assert findings_dict[crit_dir].severity == "critical"


def test_analyzer_suppresses_safe_path(tmp_path: Path) -> None:
    safe_dir = tmp_path / "safe-zone"
    unsafe_dir = tmp_path / "unsafe-zone"

    for i in range(4):
        _write_file(safe_dir / f"f-{i}.bin", 100)
        _write_file(unsafe_dir / f"f-{i}.bin", 100)

    inventory = scan_file_inventory(tmp_path, tiny_file_max_bytes=4096)
    report = analyze_tiny_file_hotspots(
        inventory,
        warning_threshold=2,
        critical_threshold=5,
        safe_paths=[safe_dir],
    )

    # safe_dir should be in suppressed, unsafe_dir in findings
    assert len(report.findings) == 1
    assert report.findings[0].path == unsafe_dir

    assert len(report.suppressed) == 1
    assert report.suppressed[0].path == safe_dir
