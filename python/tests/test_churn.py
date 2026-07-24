"""Tests for the churn velocity analyzer."""

from viper_health.analyzers.churn import compute_churn
from viper_health.collectors.snapshot import Snapshot, SnapshotEntry


def _snap(ts: str, entries: list[SnapshotEntry]) -> Snapshot:
    return Snapshot(timestamp_utc=ts, host="h", entries=tuple(entries))


def test_no_churn_when_identical():
    entry = SnapshotEntry("cache", "browser_cache", "C:/cache", 100, 1000, 50)
    prev = _snap("2024-01-01T00:00:00+00:00", [entry])
    curr = _snap("2024-01-02T00:00:00+00:00", [entry])

    report = compute_churn(prev, curr)
    assert report.overall_severity == "good"
    assert report.findings[0].files_delta == 0
    assert report.findings[0].risk_label == "stable"


def test_warning_growth():
    prev = _snap("2024-01-01T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 0, 0, 0)])
    # 15,000 files added in 1 day -> warning (>= 10k)
    curr = _snap("2024-01-02T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 15_000, 0, 0)])

    report = compute_churn(prev, curr)
    assert report.overall_severity == "warning"
    assert report.findings[0].risk_label == "existing"
    assert report.findings[0].files_per_day == 15_000


def test_critical_growth():
    prev = _snap("2024-01-01T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 0, 0, 0)])
    # 30,000 in 1 day -> critical (>= 25k)
    curr = _snap("2024-01-02T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 30_000, 0, 0)])

    report = compute_churn(prev, curr)
    assert report.overall_severity == "critical"
    assert report.critical_count == 1


def test_new_risk_label():
    prev = _snap("2024-01-01T00:00:00+00:00", [])
    curr = _snap("2024-01-02T00:00:00+00:00",
                 [SnapshotEntry("new", "cloud_sync", "C:/new", 5, 50, 5)])

    report = compute_churn(prev, curr)
    assert report.findings[0].risk_label == "new"


def test_resolved_risk_label():
    prev = _snap("2024-01-01T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 1000, 0, 0)])
    curr = _snap("2024-01-02T00:00:00+00:00",
                 [SnapshotEntry("c", "browser_cache", "C:/c", 200, 0, 0)])

    report = compute_churn(prev, curr)
    assert report.findings[0].risk_label == "resolved"
    assert report.findings[0].files_delta == -800


def test_elapsed_days_floor_prevents_inflation():
    # Same timestamp -> elapsed floored to 1 hour, not zero
    entry_prev = SnapshotEntry("c", "browser_cache", "C:/c", 0, 0, 0)
    entry_curr = SnapshotEntry("c", "browser_cache", "C:/c", 100, 0, 0)
    prev = _snap("2024-01-01T00:00:00+00:00", [entry_prev])
    curr = _snap("2024-01-01T00:00:00+00:00", [entry_curr])

    report = compute_churn(prev, curr)
    # 100 files / (1/24 day) = 2400 files/day, finite
    assert report.elapsed_days > 0
    assert report.findings[0].files_per_day == 2400.0
