"""Filesystem inventory collector focused on tiny-file pressure signals."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DirectoryStats:
    """Aggregated counters for a directory path."""

    total_files: int = 0
    tiny_files: int = 0
    total_bytes: int = 0


@dataclass(frozen=True)
class InventoryResult:
    """High-level inventory statistics for a scanned tree."""

    root: str
    tiny_file_max_bytes: int
    total_files: int
    tiny_files: int
    total_bytes: int
    directories_scanned: int
    per_directory: dict[str, DirectoryStats]


def _increment_stats(existing: DirectoryStats, *, size_bytes: int, is_tiny: bool) -> DirectoryStats:
    return DirectoryStats(
        total_files=existing.total_files + 1,
        tiny_files=existing.tiny_files + (1 if is_tiny else 0),
        total_bytes=existing.total_bytes + size_bytes,
    )


def scan_file_inventory(
    root: Path | str,
    *,
    tiny_file_max_bytes: int = 4096,
    progress_callback: Callable[[int, int, str], None] | None = None,
    progress_interval: int = 100,
) -> InventoryResult:
    """Scan a directory tree and aggregate tiny-file statistics.

    Parameters
    ----------
    root:
        Root directory to scan recursively.
    tiny_file_max_bytes:
        File size threshold (inclusive) for tiny-file classification.
    progress_callback:
        Optional callback(directories_scanned, files_scanned, current_dir) for progress reporting.
    progress_interval:
        How often to call progress_callback (every N directories).
    """

    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Root path does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root_path}")

    total_files = 0
    tiny_files = 0
    total_bytes = 0
    per_directory: dict[str, DirectoryStats] = {}
    directories_scanned = 0

    for dirpath, _, filenames in root_path.walk():
        directories_scanned += 1
        dir_key = str(dirpath.resolve())
        per_directory.setdefault(dir_key, DirectoryStats())
        
        # Report progress periodically
        if progress_callback and directories_scanned % progress_interval == 0:
            progress_callback(directories_scanned, total_files, str(dirpath))

        for filename in filenames:
            file_path = dirpath / filename
            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                # Ignore transient filesystem access issues for now.
                continue

            is_tiny = size_bytes <= tiny_file_max_bytes

            total_files += 1
            total_bytes += size_bytes
            if is_tiny:
                tiny_files += 1

            per_directory[dir_key] = _increment_stats(
                per_directory[dir_key],
                size_bytes=size_bytes,
                is_tiny=is_tiny,
            )

    return InventoryResult(
        root=str(root_path),
        tiny_file_max_bytes=tiny_file_max_bytes,
        total_files=total_files,
        tiny_files=tiny_files,
        total_bytes=total_bytes,
        directories_scanned=directories_scanned,
        per_directory=per_directory,
    )
