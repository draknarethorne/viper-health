"""
Lean filesystem tree counter.

Provides lightweight recursive counting of files, bytes, and tiny files
without building a per-directory map. Suitable for large cache/churn roots
where only aggregate totals are needed and memory must stay bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TreeCount:
    """Aggregate counters for a scanned tree."""

    file_count: int
    total_bytes: int
    tiny_files: int
    directories: int
    errors: int


def count_tree(
    root: Path | str,
    *,
    tiny_file_max_bytes: int = 4096,
    follow_symlinks: bool = False,
) -> TreeCount:
    """
    Recursively count files, bytes, and tiny files under ``root``.

    Reparse points (symlinks/junctions) are not traversed by default, matching
    the safety posture of the spec (Section 8.2).

    Args:
        root: Directory to scan.
        tiny_file_max_bytes: Inclusive size threshold for tiny-file classification.
        follow_symlinks: Whether to traverse reparse points (default False).

    Returns:
        TreeCount with aggregate metrics. Missing roots return an all-zero count
        with ``errors`` incremented so callers can distinguish "empty" from
        "unavailable".
    """
    root_path = Path(root)

    file_count = 0
    total_bytes = 0
    tiny_files = 0
    directories = 0
    errors = 0

    if not root_path.exists():
        return TreeCount(0, 0, 0, 0, 1)

    if not root_path.is_dir():
        # Single file target
        try:
            size = root_path.stat().st_size
            is_tiny = size <= tiny_file_max_bytes
            return TreeCount(1, size, 1 if is_tiny else 0, 0, 0)
        except OSError:
            return TreeCount(0, 0, 0, 0, 1)

    try:
        walker = root_path.walk(on_error=lambda _e: None, follow_symlinks=follow_symlinks)
    except TypeError:
        # Older signature fallback (shouldn't happen on 3.12+ but be safe)
        walker = root_path.walk()

    for dirpath, _dirnames, filenames in walker:
        directories += 1
        for filename in filenames:
            file_path = dirpath / filename
            try:
                size = file_path.stat().st_size
            except OSError:
                errors += 1
                continue

            file_count += 1
            total_bytes += size
            if size <= tiny_file_max_bytes:
                tiny_files += 1

    return TreeCount(
        file_count=file_count,
        total_bytes=total_bytes,
        tiny_files=tiny_files,
        directories=directories,
        errors=errors,
    )


def bytes_to_gib(value: int) -> float:
    """Convert bytes to gibibytes."""
    return value / (1024 ** 3)


def bytes_to_mib(value: int) -> float:
    """Convert bytes to mebibytes."""
    return value / (1024 ** 2)


def format_bytes(value: float, *, decimals: int | None = None) -> str:
    """Format a byte count as an auto-scaled, Windows-consistent size string.

    Uses binary magnitudes (1 GB = 1024 MB, matching Windows Explorer and the
    rest of the toolkit) but the conventional GB/MB/TB/KB labels. Negative
    values are formatted with a leading sign.

    Args:
        value: Byte count (may be negative).
        decimals: Fixed decimal places; when None, scales precision by unit
            (2 for GB/TB, 1 for MB/KB, 0 for bytes).
    """
    sign = "-" if value < 0 else ""
    magnitude = abs(float(value))
    for unit, threshold, default_dp in (
        ("TB", 1024 ** 4, 2),
        ("GB", 1024 ** 3, 2),
        ("MB", 1024 ** 2, 1),
        ("KB", 1024, 1),
    ):
        if magnitude >= threshold:
            places = default_dp if decimals is None else decimals
            return f"{sign}{magnitude / threshold:.{places}f} {unit}"
    places = 0 if decimals is None else decimals
    return f"{sign}{magnitude:.{places}f} B"

