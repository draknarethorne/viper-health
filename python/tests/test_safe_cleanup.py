"""Tests for the safety-gated cleanup engine."""

from viper_health.collectors.reclaimable_space import CAUTION, SAFE, ReclaimTarget
from viper_health.maintenance.safe_cleanup import (
    DELETE,
    QUARANTINE,
    execute_cleanup,
    is_actionable,
    is_under,
    plan_cleanup,
)


def _target(path, *, safety=SAFE, auto=True, name="Temp"):
    return ReclaimTarget(
        name=name,
        category="temp",
        path=str(path),
        exists=True,
        size_bytes=0,
        file_count=0,
        tiny_files=0,
        safety_class=safety,
        regenerates=True,
        requires_admin=False,
        reclaim_hint="hint",
        auto_cleanable=auto,
    )


def _make_files(root, count=3):
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (root / f"f{i}.tmp").write_bytes(b"x" * 100)


def test_is_under_and_actionable(tmp_path):
    allowed = tmp_path / "allowed"
    immut = tmp_path / "system"
    allowed.mkdir()
    immut.mkdir()

    assert is_under(allowed / "a.txt", [str(allowed)]) is True
    assert is_under(immut / "a.txt", [str(allowed)]) is False

    ok, _ = is_actionable(allowed / "a.txt", allowed_roots=[str(allowed)], immutable_roots=[str(immut)])
    assert ok is True

    ok, reason = is_actionable(immut / "a.txt", allowed_roots=[str(immut)], immutable_roots=[str(immut)])
    assert ok is False
    assert "immutable" in reason


def test_plan_includes_allowed_auto_cleanable(tmp_path):
    root = tmp_path / "allowed" / "Temp"
    _make_files(root, 3)

    actions, stopped = plan_cleanup(
        [_target(root)],
        allowed_roots=[str(tmp_path / "allowed")],
        immutable_roots=[],
    )

    assert stopped is None
    pending = [a for a in actions if a.action == "pending"]
    assert len(pending) == 3


def test_plan_skips_non_auto_cleanable(tmp_path):
    root = tmp_path / "allowed"
    _make_files(root, 2)
    actions, _ = plan_cleanup(
        [_target(root, auto=False)],
        allowed_roots=[str(tmp_path)],
        immutable_roots=[],
    )
    assert all(a.action != "pending" for a in actions)


def test_plan_skips_caution_class(tmp_path):
    root = tmp_path / "allowed"
    _make_files(root, 2)
    actions, _ = plan_cleanup(
        [_target(root, safety=CAUTION)],
        allowed_roots=[str(tmp_path)],
        immutable_roots=[],
    )
    assert all(a.action != "pending" for a in actions)


def test_plan_rejects_immutable_target(tmp_path):
    root = tmp_path / "system" / "Temp"
    _make_files(root, 2)
    actions, _ = plan_cleanup(
        [_target(root)],
        allowed_roots=[str(tmp_path)],
        immutable_roots=[str(tmp_path / "system")],
    )
    skips = [a for a in actions if a.action == "skip"]
    assert skips and "immutable" in skips[0].reason


def test_plan_enforces_file_cap(tmp_path):
    root = tmp_path / "allowed" / "Temp"
    _make_files(root, 5)
    actions, stopped = plan_cleanup(
        [_target(root)],
        allowed_roots=[str(tmp_path / "allowed")],
        immutable_roots=[],
        max_files=2,
    )
    assert stopped is not None and "file cap" in stopped
    assert len([a for a in actions if a.action == "pending"]) == 2


def test_execute_dry_run_changes_nothing(tmp_path):
    root = tmp_path / "allowed" / "Temp"
    _make_files(root, 3)
    actions, _ = plan_cleanup([_target(root)], allowed_roots=[str(tmp_path / "allowed")], immutable_roots=[])

    result = execute_cleanup(actions, dry_run=True, manifest_dir=tmp_path / "m")

    assert result.dry_run is True
    assert result.files_actioned == 3
    # Files must still exist.
    assert len(list(root.glob("*.tmp"))) == 3
    assert result.manifest_path is not None


def test_execute_quarantine_moves_files(tmp_path):
    root = tmp_path / "allowed" / "Temp"
    _make_files(root, 3)
    actions, _ = plan_cleanup([_target(root)], allowed_roots=[str(tmp_path / "allowed")], immutable_roots=[])
    quarantine = tmp_path / "q"

    result = execute_cleanup(
        actions, dry_run=False, mode=QUARANTINE, quarantine_dir=quarantine, manifest_dir=quarantine
    )

    assert result.files_actioned == 3
    assert list(root.glob("*.tmp")) == []  # originals moved
    assert result.quarantine_dir is not None
    # Quarantined copies exist somewhere under the quarantine dir.
    moved = list(Path_glob(result.quarantine_dir))
    assert len(moved) == 3


def test_execute_delete_removes_files(tmp_path):
    root = tmp_path / "allowed" / "Temp"
    _make_files(root, 2)
    actions, _ = plan_cleanup([_target(root)], allowed_roots=[str(tmp_path / "allowed")], immutable_roots=[])

    result = execute_cleanup(actions, dry_run=False, mode=DELETE, manifest_dir=tmp_path / "m")

    assert result.files_actioned == 2
    assert list(root.glob("*.tmp")) == []


def Path_glob(directory):
    from pathlib import Path

    return [p for p in Path(directory).rglob("*.tmp") if p.is_file()]
