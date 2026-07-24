"""
Point-in-time snapshot capture for trend and churn analysis.

Snapshots record file counts and sizes for a set of target roots at a moment
in time. Comparing two snapshots yields churn velocity (files/day, bytes/day)
and acceleration signals per spec Section 11.

Snapshots are stored as JSON under data/snapshots/ by convention.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from viper_health.collectors.target_roots import TargetRoot
from viper_health.utils.fs_counter import count_tree


@dataclass(frozen=True)
class SnapshotEntry:
    """Recorded metrics for a single target root."""

    name: str
    category: str
    path: str
    file_count: int
    total_bytes: int
    tiny_files: int


@dataclass(frozen=True)
class Snapshot:
    """A point-in-time capture across multiple target roots."""

    timestamp_utc: str
    host: str
    entries: tuple[SnapshotEntry, ...]

    def to_dict(self) -> dict:
        return {
            "timestamp_utc": self.timestamp_utc,
            "host": self.host,
            "entries": [asdict(e) for e in self.entries],
        }


def capture_snapshot(
    roots: list[TargetRoot],
    *,
    host: str | None = None,
    tiny_file_max_bytes: int = 4096,
) -> Snapshot:
    """
    Capture a snapshot of file metrics for the given target roots.

    Args:
        roots: Target roots to measure.
        host: Optional host identifier; defaults to platform node name.
        tiny_file_max_bytes: Tiny-file classification threshold.

    Returns:
        Snapshot with one entry per existing root.
    """
    import platform

    if host is None:
        host = platform.node()

    entries: list[SnapshotEntry] = []
    for root in roots:
        if not root.exists:
            continue
        count = count_tree(root.path, tiny_file_max_bytes=tiny_file_max_bytes)
        entries.append(
            SnapshotEntry(
                name=root.name,
                category=root.category,
                path=str(root.path),
                file_count=count.file_count,
                total_bytes=count.total_bytes,
                tiny_files=count.tiny_files,
            )
        )

    return Snapshot(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        host=host,
        entries=tuple(entries),
    )


def save_snapshot(snapshot: Snapshot, output_path: Path) -> None:
    """Write a snapshot to a JSON file, creating parent directories."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, indent=2)


def load_snapshot(path: Path) -> Snapshot:
    """
    Load a snapshot from a JSON file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is not a valid snapshot.
    """
    if not path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if "timestamp_utc" not in data or "entries" not in data:
        raise ValueError(f"Invalid snapshot file: {path}")

    entries = tuple(
        SnapshotEntry(
            name=e["name"],
            category=e.get("category", "unknown"),
            path=e["path"],
            file_count=e["file_count"],
            total_bytes=e["total_bytes"],
            tiny_files=e.get("tiny_files", 0),
        )
        for e in data["entries"]
    )

    return Snapshot(
        timestamp_utc=data["timestamp_utc"],
        host=data.get("host", "unknown"),
        entries=entries,
    )
