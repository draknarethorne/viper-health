"""Safety-gated cleanup engine for low-risk reclaimable space.

This is the only cleanup path in viper-health that can modify the filesystem,
and it is constrained by the project safety model:

- **Dry-run by default.** Nothing is touched unless ``dry_run=False``.
- **Allowlist + immutable enforcement.** A file is only actionable if it lives
  under an approved cleanup root and NOT under any immutable/system root.
- **Auto-cleanable only.** Only ``ReclaimTarget`` entries flagged
  ``auto_cleanable`` (regenerating temp/log/crash junk) are eligible. Browser
  and app caches, the recycle bin, update caches, and user data are never
  auto-cleaned — they are reported with manual guidance instead.
- **Quarantine-first.** The default action moves files into a timestamped
  quarantine directory; hard delete requires an explicit choice.
- **Action caps + kill switch.** Cleanup stops when a file/byte cap is hit or
  the kill switch reports stop.
- **Manifest.** Every planned/performed action is recorded to a JSON manifest.

Files that are locked/in use are skipped, never forced.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from viper_health.collectors.reclaimable_space import SAFE, ReclaimTarget

QUARANTINE = "quarantine"
DELETE = "delete"

# Conservative default caps to prevent runaway operations.
DEFAULT_MAX_FILES = 200_000
DEFAULT_MAX_BYTES = 50 * 1024**3  # 50 GiB


@dataclass(frozen=True)
class PlannedAction:
    """A single file scheduled for cleanup (or skipped, with a reason)."""

    path: str
    size_bytes: int
    target_name: str
    action: str  # "quarantine" | "delete" | "skip"
    reason: str = ""


@dataclass
class CleanupResult:
    """Outcome of a cleanup run."""

    dry_run: bool
    mode: str
    files_actioned: int
    bytes_reclaimed: int
    files_skipped: int
    stopped_reason: str | None
    quarantine_dir: str | None
    manifest_path: str | None
    actions: list[PlannedAction] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _norm(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.path.expandvars(str(path))))


def is_under(path: str | Path, roots: list[str]) -> bool:
    """Return True if ``path`` is equal to or nested under any of ``roots``."""
    target = _norm(path)
    for root in roots:
        root_norm = _norm(root)
        if target == root_norm or target.startswith(root_norm + os.sep):
            return True
    return False


def is_actionable(
    path: str | Path,
    *,
    allowed_roots: list[str],
    immutable_roots: list[str],
) -> tuple[bool, str]:
    """Decide whether a path may be cleaned. Returns (ok, reason_if_not)."""
    if is_under(path, immutable_roots):
        return False, "under immutable/system root"
    if not is_under(path, allowed_roots):
        return False, "outside approved cleanup allowlist"
    return True, ""


def plan_cleanup(
    targets: list[ReclaimTarget],
    *,
    allowed_roots: list[str],
    immutable_roots: list[str],
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[list[PlannedAction], str | None]:
    """Build a per-file cleanup plan honoring safety gates and caps.

    Only ``auto_cleanable`` SAFE targets under the allowlist (and not immutable)
    contribute files. Returns (actions, stopped_reason). ``stopped_reason`` is
    set when a cap halts planning.
    """
    actions: list[PlannedAction] = []
    total_files = 0
    total_bytes = 0
    stopped_reason: str | None = None

    for target in targets:
        if not (target.auto_cleanable and target.safety_class == SAFE):
            continue
        ok, reason = is_actionable(
            target.path, allowed_roots=allowed_roots, immutable_roots=immutable_roots
        )
        if not ok:
            actions.append(
                PlannedAction(target.path, target.size_bytes, target.name, "skip", reason)
            )
            continue

        root = Path(target.path)
        if not root.exists():
            continue

        for file_path in _iter_files(root):
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if total_files + 1 > max_files:
                stopped_reason = f"file cap reached ({max_files})"
                return actions, stopped_reason
            if total_bytes + size > max_bytes:
                stopped_reason = f"byte cap reached ({max_bytes})"
                return actions, stopped_reason
            total_files += 1
            total_bytes += size
            actions.append(
                PlannedAction(str(file_path), size, target.name, "pending")
            )

    return actions, stopped_reason


def _iter_files(root: Path):
    try:
        walker = root.walk(on_error=lambda _e: None, follow_symlinks=False)
    except (TypeError, AttributeError):  # pragma: no cover - 3.12 baseline
        return
    for dirpath, _dirnames, filenames in walker:
        for filename in filenames:
            yield dirpath / filename


def execute_cleanup(
    actions: list[PlannedAction],
    *,
    dry_run: bool = True,
    mode: str = QUARANTINE,
    quarantine_dir: Path | None = None,
    manifest_dir: Path | None = None,
    kill_switch: Callable[[], bool] | None = None,
    stopped_reason: str | None = None,
) -> CleanupResult:
    """Apply (or simulate) a cleanup plan.

    Args:
        actions: Plan from :func:`plan_cleanup` (pending items are acted on).
        dry_run: When True (default) nothing is modified.
        mode: ``quarantine`` (default, reversible) or ``delete`` (irreversible).
        quarantine_dir: Destination for quarantined files (required for real
            quarantine runs).
        manifest_dir: Where to write the JSON manifest (defaults alongside
            quarantine_dir or cwd).
        kill_switch: Optional callable; when it returns True, cleanup stops.

    Returns:
        A :class:`CleanupResult` with counts and the manifest path.
    """
    performed: list[PlannedAction] = []
    files_actioned = 0
    bytes_reclaimed = 0
    files_skipped = 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    quarantine_root: Path | None = None
    if mode == QUARANTINE and not dry_run:
        quarantine_root = (quarantine_dir or Path.cwd() / "quarantine") / stamp
        quarantine_root.mkdir(parents=True, exist_ok=True)

    for action in actions:
        if action.action == "skip":
            performed.append(action)
            files_skipped += 1
            continue
        if kill_switch is not None and kill_switch():
            stopped_reason = stopped_reason or "kill switch engaged"
            break

        if dry_run:
            performed.append(
                PlannedAction(action.path, action.size_bytes, action.target_name, mode, "dry-run")
            )
            files_actioned += 1
            bytes_reclaimed += action.size_bytes
            continue

        try:
            if mode == DELETE:
                Path(action.path).unlink()
            else:
                _quarantine_file(Path(action.path), quarantine_root)  # type: ignore[arg-type]
        except (PermissionError, OSError) as exc:
            performed.append(
                PlannedAction(action.path, action.size_bytes, action.target_name, "skip", f"in use / {exc.__class__.__name__}")
            )
            files_skipped += 1
            continue

        performed.append(
            PlannedAction(action.path, action.size_bytes, action.target_name, mode)
        )
        files_actioned += 1
        bytes_reclaimed += action.size_bytes

    manifest_path = _write_manifest(
        performed,
        manifest_dir=manifest_dir or (quarantine_root or Path.cwd()),
        stamp=stamp,
        dry_run=dry_run,
        mode=mode,
    )

    return CleanupResult(
        dry_run=dry_run,
        mode=mode,
        files_actioned=files_actioned,
        bytes_reclaimed=bytes_reclaimed,
        files_skipped=files_skipped,
        stopped_reason=stopped_reason,
        quarantine_dir=str(quarantine_root) if quarantine_root else None,
        manifest_path=str(manifest_path),
        actions=performed,
    )


def _quarantine_file(source: Path, quarantine_root: Path) -> None:
    """Move a file into the quarantine tree, preserving a flat drive-relative path."""
    drive, tail = os.path.splitdrive(str(source))
    drive_label = drive.replace(":", "").strip("\\/ ") or "root"
    destination = quarantine_root / drive_label / tail.lstrip("\\/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def _write_manifest(
    actions: list[PlannedAction],
    *,
    manifest_dir: Path,
    stamp: str,
    dry_run: bool,
    mode: str,
) -> Path:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"cleanup-manifest-{stamp}.json"
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "mode": mode,
        "action_count": len(actions),
        "actions": [asdict(action) for action in actions],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path
