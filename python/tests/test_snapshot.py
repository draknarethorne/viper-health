"""Tests for snapshot capture/save/load."""

from pathlib import Path

import pytest

from viper_health.collectors.snapshot import (
    Snapshot,
    SnapshotEntry,
    capture_snapshot,
    load_snapshot,
    save_snapshot,
)
from viper_health.collectors.target_roots import TargetRoot


def test_capture_snapshot_counts(tmp_path: Path):
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    (tmp_path / "b.txt").write_bytes(b"y" * 20)
    root = TargetRoot("test", "cloud_sync", tmp_path, True)

    snapshot = capture_snapshot([root], host="testhost")
    assert snapshot.host == "testhost"
    assert len(snapshot.entries) == 1
    assert snapshot.entries[0].file_count == 2


def test_capture_snapshot_skips_missing(tmp_path: Path):
    missing = tmp_path / "gone"
    root = TargetRoot("missing", "cloud_sync", missing, False)
    snapshot = capture_snapshot([root])
    assert len(snapshot.entries) == 0


def test_save_and_load_roundtrip(tmp_path: Path):
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    root = TargetRoot("test", "cloud_sync", tmp_path, True)
    snapshot = capture_snapshot([root], host="h1")

    out = tmp_path / "snapshots" / "snap.json"
    save_snapshot(snapshot, out)
    assert out.exists()

    loaded = load_snapshot(out)
    assert loaded.host == "h1"
    assert len(loaded.entries) == 1
    assert loaded.entries[0].file_count == 1


def test_load_missing_snapshot(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path / "nope.json")


def test_load_invalid_snapshot(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a snapshot"}')
    with pytest.raises(ValueError, match="Invalid snapshot"):
        load_snapshot(bad)


def test_snapshot_to_dict():
    entry = SnapshotEntry("n", "cat", "p", 5, 100, 2)
    snap = Snapshot("2024-01-01T00:00:00+00:00", "host", (entry,))
    d = snap.to_dict()
    assert d["host"] == "host"
    assert d["entries"][0]["file_count"] == 5
