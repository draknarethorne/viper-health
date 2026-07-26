"""Reclaimable-space detector (observe-only).

Measures well-known Windows cleanup locations (Recycle Bin, temp folders,
browser/app caches, update residue, crash dumps, logs) and classifies each by
how safe it is to clear. This detector is **read-only**: it never deletes,
moves, or modifies anything. It reports sizes and the safe, manual reclaim
command for each target so the operator can decide.

Safety classes:
- ``safe``     — caches/temp that regenerate automatically; low risk to clear.
- ``caution``  — clearing is fine but has a side effect (admin needed, service
                 must be stopped, or a one-time slowdown as caches rebuild).
- ``review``   — may contain user data; reported for awareness, never a cleanup
                 recommendation.

Immutable/system-critical roots are intentionally excluded from candidates.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from viper_health.utils.fs_counter import count_tree

SAFE = "safe"
CAUTION = "caution"
REVIEW = "review"

# Categories that are genuinely safe to clear automatically while the system is
# running (they hold regenerating system junk, not app profiles or user data).
# Browser/app caches are deliberately excluded because clearing them while the
# app is open can corrupt the profile; the recycle bin uses the shell API.
AUTO_CLEANABLE_CATEGORIES = frozenset({"temp", "system_cache", "crash_dumps", "telemetry_log"})


@dataclass(frozen=True)
class ReclaimTargetSpec:
    """Definition of a candidate cleanup location."""

    name: str
    category: str
    template: str
    safety_class: str
    regenerates: bool
    requires_admin: bool
    reclaim_hint: str


@dataclass(frozen=True)
class ReclaimTarget:
    """A measured cleanup candidate."""

    name: str
    category: str
    path: str
    exists: bool
    size_bytes: int
    file_count: int
    tiny_files: int
    safety_class: str
    regenerates: bool
    requires_admin: bool
    reclaim_hint: str
    auto_cleanable: bool = False
    error: str | None = None


@dataclass(frozen=True)
class ReclaimReport:
    """Aggregated reclaimable-space findings."""

    targets: list[ReclaimTarget]
    safe_bytes: int
    caution_bytes: int
    review_bytes: int
    total_reclaimable_bytes: int  # safe + caution (existing targets only)
    by_category: dict[str, int] = field(default_factory=dict)


# Curated cleanup candidates. Ordered roughly by typical payoff.
_TARGET_SPECS: tuple[ReclaimTargetSpec, ...] = (
    ReclaimTargetSpec(
        "Recycle Bin", "recycle_bin", r"%SystemDrive%\$Recycle.Bin", SAFE, True, False,
        "Empty via Settings > System > Storage, or PowerShell: Clear-RecycleBin -Force",
    ),
    ReclaimTargetSpec(
        "User Temp", "temp", r"%LOCALAPPDATA%\Temp", SAFE, True, False,
        "Enable Storage Sense, or run Disk Cleanup (cleanmgr). Files in use are skipped.",
    ),
    ReclaimTargetSpec(
        "Windows Temp", "temp", r"%WINDIR%\Temp", SAFE, True, True,
        "Run Disk Cleanup (cleanmgr) as admin; clears system temp safely.",
    ),
    ReclaimTargetSpec(
        "Thumbnail/Icon cache", "system_cache", r"%LOCALAPPDATA%\Microsoft\Windows\Explorer", SAFE, True, False,
        "Disk Cleanup > Thumbnails. Rebuilds automatically on next browse.",
    ),
    ReclaimTargetSpec(
        "INetCache", "system_cache", r"%LOCALAPPDATA%\Microsoft\Windows\INetCache", SAFE, True, False,
        "Disk Cleanup > Temporary Internet Files.",
    ),
    ReclaimTargetSpec(
        "Crash dumps", "crash_dumps", r"%LOCALAPPDATA%\CrashDumps", SAFE, True, False,
        "Safe to delete once any crash has been investigated.",
    ),
    ReclaimTargetSpec(
        "Edge cache", "browser_cache", r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache", SAFE, True, False,
        "Clear from Edge: Settings > Privacy > Clear browsing data > Cached files.",
    ),
    ReclaimTargetSpec(
        "Chrome cache", "browser_cache", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", SAFE, True, False,
        "Clear from Chrome: Settings > Privacy > Clear browsing data > Cached images/files.",
    ),
    ReclaimTargetSpec(
        "Chrome code cache", "browser_cache", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache", SAFE, True, False,
        "Cleared with Chrome cached files; regenerates.",
    ),
    ReclaimTargetSpec(
        "Firefox cache", "browser_cache", r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2", SAFE, True, False,
        "Clear from Firefox: Settings > Privacy > Cookies and Site Data > Clear Data.",
    ),
    ReclaimTargetSpec(
        "Discord cache", "app_cache", r"%APPDATA%\discord\Cache", SAFE, True, False,
        "Safe to delete while Discord is closed; regenerates.",
    ),
    ReclaimTargetSpec(
        "Teams cache", "app_cache", r"%APPDATA%\Microsoft\Teams\Cache", SAFE, True, False,
        "Safe to delete while Teams is closed; regenerates.",
    ),
    ReclaimTargetSpec(
        "WER report queue", "telemetry_log", r"%LOCALAPPDATA%\Microsoft\Windows\WER\ReportQueue", SAFE, True, False,
        "Disk Cleanup > System error memory/queued error reports.",
    ),
    ReclaimTargetSpec(
        "Delivery Optimization cache", "update_residue", r"%WINDIR%\SoftwareDistribution\DeliveryOptimization", CAUTION, True, True,
        "Disk Cleanup > Delivery Optimization Files (admin).",
    ),
    ReclaimTargetSpec(
        "Windows Update download cache", "update_residue", r"%WINDIR%\SoftwareDistribution\Download", CAUTION, True, True,
        "Stop the wuauserv service first, then clear (admin). Rebuilds on next update.",
    ),
    ReclaimTargetSpec(
        "CBS logs", "telemetry_log", r"%WINDIR%\Logs\CBS", CAUTION, True, True,
        "Disk Cleanup handles these; safe once servicing is stable (admin).",
    ),
    ReclaimTargetSpec(
        "Prefetch", "system_cache", r"%WINDIR%\Prefetch", CAUTION, True, True,
        "Clearing causes a one-time slower launch as prefetch data rebuilds (admin).",
    ),
    ReclaimTargetSpec(
        "Downloads (user data)", "user_data", r"%USERPROFILE%\Downloads", REVIEW, False, False,
        "Review manually — this is your data. Move large installers elsewhere if not needed.",
    ),
)


def _expand_paths(template: str) -> list[Path]:
    """Expand env vars and a single ``*`` glob segment into concrete paths."""
    expanded = os.path.expandvars(template)
    if "*" not in expanded:
        return [Path(expanded)]

    parts = Path(expanded).parts
    # Split at the first component containing a wildcard.
    for index, part in enumerate(parts):
        if "*" in part:
            base = Path(*parts[:index]) if index else Path(parts[0])
            pattern = str(Path(*parts[index:]))
            try:
                return sorted(base.glob(pattern))
            except OSError:
                return []
    return [Path(expanded)]


def _measure(path: Path) -> tuple[bool, int, int, int, str | None]:
    """Return (exists, size_bytes, file_count, tiny_files, error) for a path."""
    if not path.exists():
        return False, 0, 0, 0, None
    count = count_tree(path)
    error = f"{count.errors} unreadable entr{'y' if count.errors == 1 else 'ies'}" if count.errors else None
    return True, count.total_bytes, count.file_count, count.tiny_files, error


def scan_reclaimable_space(*, include_empty: bool = False) -> ReclaimReport:
    """Measure all curated cleanup candidates (observe-only).

    Args:
        include_empty: Include targets that do not exist or are empty.

    Returns:
        A ``ReclaimReport`` with per-target sizes and safety classification.
        Nothing is deleted or modified.
    """
    targets: list[ReclaimTarget] = []
    for spec in _TARGET_SPECS:
        for path in _expand_paths(spec.template):
            exists, size_bytes, file_count, tiny_files, error = _measure(path)
            if not exists and not include_empty:
                continue
            if exists and size_bytes == 0 and file_count == 0 and not include_empty:
                continue
            auto_cleanable = (
                spec.safety_class == SAFE and spec.category in AUTO_CLEANABLE_CATEGORIES
            )
            targets.append(
                ReclaimTarget(
                    name=spec.name,
                    category=spec.category,
                    path=str(path),
                    exists=exists,
                    size_bytes=size_bytes,
                    file_count=file_count,
                    tiny_files=tiny_files,
                    safety_class=spec.safety_class,
                    regenerates=spec.regenerates,
                    requires_admin=spec.requires_admin,
                    reclaim_hint=spec.reclaim_hint,
                    auto_cleanable=auto_cleanable,
                    error=error,
                )
            )

    safe_bytes = sum(t.size_bytes for t in targets if t.safety_class == SAFE)
    caution_bytes = sum(t.size_bytes for t in targets if t.safety_class == CAUTION)
    review_bytes = sum(t.size_bytes for t in targets if t.safety_class == REVIEW)

    by_category: dict[str, int] = {}
    for target in targets:
        by_category[target.category] = by_category.get(target.category, 0) + target.size_bytes

    # Sort largest first for reporting.
    targets.sort(key=lambda t: t.size_bytes, reverse=True)

    return ReclaimReport(
        targets=targets,
        safe_bytes=safe_bytes,
        caution_bytes=caution_bytes,
        review_bytes=review_bytes,
        total_reclaimable_bytes=safe_bytes + caution_bytes,
        by_category=by_category,
    )
