"""Tests for the category pressure analyzer."""

from pathlib import Path

from viper_health.analyzers.category_pressure import (
    CategoryThresholds,
    analyze_category,
)
from viper_health.collectors.target_roots import TargetRoot


def _make_root(name: str, path: Path, category: str = "browser_cache") -> TargetRoot:
    return TargetRoot(name=name, category=category, path=path, exists=path.exists())


def test_analyze_category_good(tmp_path: Path):
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    roots = [_make_root("cache", tmp_path)]

    report = analyze_category("browser_cache", roots)
    assert report.overall_severity == "good"
    assert report.total_files == 1
    assert report.good_count == 1


def test_analyze_category_warning_by_file_count(tmp_path: Path):
    roots = [_make_root("cache", tmp_path)]
    thresholds = CategoryThresholds(
        file_count_warning=1,
        file_count_critical=100,
        size_warning_bytes=10**12,
        size_critical_bytes=10**15,
    )
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    (tmp_path / "b.txt").write_bytes(b"y" * 10)

    report = analyze_category("browser_cache", roots, thresholds=thresholds)
    assert report.overall_severity == "warning"
    assert report.warning_count == 1


def test_analyze_category_critical_by_size(tmp_path: Path):
    roots = [_make_root("cache", tmp_path)]
    thresholds = CategoryThresholds(
        file_count_warning=10**9,
        file_count_critical=10**12,
        size_warning_bytes=10,
        size_critical_bytes=50,
    )
    (tmp_path / "big.bin").write_bytes(b"z" * 100)

    report = analyze_category("browser_cache", roots, thresholds=thresholds)
    assert report.overall_severity == "critical"
    assert report.critical_count == 1
    assert "critical" in report.findings[0].reason


def test_analyze_category_skips_missing(tmp_path: Path):
    missing = tmp_path / "gone"
    roots = [TargetRoot("missing", "browser_cache", missing, False)]

    report = analyze_category("browser_cache", roots)
    assert report.findings == ()
    assert report.total_files == 0
    assert report.overall_severity == "good"


def test_findings_sorted_critical_first(tmp_path: Path):
    good_dir = tmp_path / "good"
    bad_dir = tmp_path / "bad"
    good_dir.mkdir()
    bad_dir.mkdir()
    (good_dir / "f.txt").write_bytes(b"x" * 10)
    for i in range(5):
        (bad_dir / f"f{i}.txt").write_bytes(b"x" * 10)

    thresholds = CategoryThresholds(
        file_count_warning=3,
        file_count_critical=4,
        size_warning_bytes=10**12,
        size_critical_bytes=10**15,
    )
    roots = [_make_root("good", good_dir), _make_root("bad", bad_dir)]
    report = analyze_category("browser_cache", roots, thresholds=thresholds)

    assert report.findings[0].severity == "critical"
    assert report.findings[0].name == "bad"
