"""Tests for reclaimable-space detection helpers."""

from viper_health.collectors.reclaimable_space import (
    AUTO_CLEANABLE_CATEGORIES,
    SAFE,
    _expand_paths,
    _measure,
    scan_reclaimable_space,
)


def test_expand_paths_without_glob():
    paths = _expand_paths(r"%LOCALAPPDATA%\Temp")
    assert len(paths) == 1
    assert "Temp" in str(paths[0])


def test_expand_paths_with_glob(tmp_path):
    (tmp_path / "p1").mkdir()
    (tmp_path / "p2").mkdir()
    (tmp_path / "p1" / "cache2").mkdir()
    (tmp_path / "p2" / "cache2").mkdir()
    template = str(tmp_path / "*" / "cache2")
    results = _expand_paths(template)
    assert len(results) == 2


def test_measure_counts_files(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 500)
    (tmp_path / "b.bin").write_bytes(b"y" * 1500)
    exists, size, files, tiny, error = _measure(tmp_path)
    assert exists is True
    assert size == 2000
    assert files == 2
    assert error is None


def test_measure_missing_path(tmp_path):
    exists, size, files, tiny, error = _measure(tmp_path / "nope")
    assert exists is False
    assert size == 0


def test_scan_returns_report_with_totals():
    report = scan_reclaimable_space(include_empty=True)
    assert hasattr(report, "targets")
    assert report.total_reclaimable_bytes == report.safe_bytes + report.caution_bytes
    # Auto-cleanable flag must only be set on SAFE targets in eligible categories.
    for target in report.targets:
        if target.auto_cleanable:
            assert target.safety_class == SAFE
            assert target.category in AUTO_CLEANABLE_CATEGORIES
