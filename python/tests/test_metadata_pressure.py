"""Tests for the composite metadata pressure analyzer."""

from viper_health.analyzers.metadata_pressure import (
    MetadataPressureThresholds,
    analyze_metadata_pressure,
)


def test_all_good():
    report = analyze_metadata_pressure(
        tiny_files_total=1000,
        directories_total=500,
    )
    assert report.overall_severity == "good"
    assert report.pressure_score == 0
    assert len(report.signals) == 2


def test_tiny_files_warning():
    report = analyze_metadata_pressure(
        tiny_files_total=300_000,  # >= 250k warning
        directories_total=500,
    )
    assert report.overall_severity == "warning"
    assert report.warning_count == 1


def test_tiny_files_critical():
    report = analyze_metadata_pressure(
        tiny_files_total=600_000,  # >= 500k critical
        directories_total=500,
    )
    assert report.overall_severity == "critical"
    assert report.critical_count == 1


def test_with_mft_signals():
    report = analyze_metadata_pressure(
        tiny_files_total=1000,
        directories_total=500,
        mft_size_bytes=int(2.6 * 1024**3),  # 2.6 GiB -> critical
        mft_fragments=12,  # >= 10 critical
    )
    assert report.overall_severity == "critical"
    # 2 base signals + 2 MFT signals
    assert len(report.signals) == 4
    assert report.critical_count == 2


def test_growth_velocity_signal():
    report = analyze_metadata_pressure(
        tiny_files_total=1000,
        directories_total=500,
        tiny_files_growth_per_day=30_000,  # >= 25k critical
    )
    assert report.overall_severity == "critical"
    growth_signals = [s for s in report.signals if s.name == "tiny_files_growth_per_day"]
    assert len(growth_signals) == 1
    assert growth_signals[0].severity == "critical"


def test_pressure_score_scaling():
    # All 4 signals critical -> score should be 100
    report = analyze_metadata_pressure(
        tiny_files_total=600_000,
        directories_total=300_000,
        mft_size_bytes=int(3 * 1024**3),
        mft_fragments=20,
    )
    assert report.pressure_score == 100


def test_custom_thresholds():
    thresholds = MetadataPressureThresholds(
        tiny_files_warning=100,
        tiny_files_critical=200,
    )
    report = analyze_metadata_pressure(
        tiny_files_total=150,
        directories_total=10,
        thresholds=thresholds,
    )
    tiny = [s for s in report.signals if s.name == "tiny_files_total"][0]
    assert tiny.severity == "warning"
