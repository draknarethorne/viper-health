"""
Well-known target roots for churn/cache detector families.

Defines the standard Windows locations for each detector family in the spec:
- Section 4.4: Cloud-sync churn (OneDrive, Google Drive, Dropbox, VS Code workspaceStorage)
- Section 4.5: Browser/WebView2 cache churn (Edge WebView2, Chrome, Discord, Teams)
- Section 4.6: Update and installer residue (SoftwareDistribution\\Download, temp staging)
- Section 4.7: Telemetry/log churn (WER, CBS logs, Temp)

All paths are expanded from environment variables and de-duplicated. Only
existing paths are returned unless ``include_missing`` is set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TargetRoot:
    """A well-known directory associated with a detector category."""

    name: str
    category: str
    path: Path
    exists: bool


# Category identifiers
CATEGORY_CLOUD_SYNC = "cloud_sync"
CATEGORY_BROWSER_CACHE = "browser_cache"
CATEGORY_UPDATE_RESIDUE = "update_residue"
CATEGORY_TELEMETRY_LOG = "telemetry_log"

ALL_CATEGORIES = (
    CATEGORY_CLOUD_SYNC,
    CATEGORY_BROWSER_CACHE,
    CATEGORY_UPDATE_RESIDUE,
    CATEGORY_TELEMETRY_LOG,
)


def _expand(path_str: str) -> Path:
    """Expand environment variables and user home in a path string."""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


# Raw target definitions: (name, path_template)
_CLOUD_SYNC_TARGETS = [
    ("OneDrive", r"%USERPROFILE%\OneDrive"),
    ("OneDrive-Commercial", r"%USERPROFILE%\OneDrive - *"),
    ("GoogleDrive-DriveFS", r"%LOCALAPPDATA%\Google\DriveFS"),
    ("Dropbox", r"%USERPROFILE%\Dropbox"),
    ("Dropbox-Cache", r"%LOCALAPPDATA%\Dropbox"),
    ("VSCode-workspaceStorage", r"%APPDATA%\Code\User\workspaceStorage"),
    ("VSCode-Insiders-workspaceStorage", r"%APPDATA%\Code - Insiders\User\workspaceStorage"),
]

_BROWSER_CACHE_TARGETS = [
    ("Edge-WebView2", r"%LOCALAPPDATA%\Microsoft\EdgeWebView\User Data"),
    ("Edge-Cache", r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"),
    ("Chrome-Cache", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"),
    ("Chrome-CodeCache", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache"),
    ("Discord-Cache", r"%APPDATA%\discord\Cache"),
    ("Discord-CodeCache", r"%APPDATA%\discord\Code Cache"),
    ("Teams-Cache", r"%APPDATA%\Microsoft\Teams\Cache"),
    ("Teams-New-Cache", r"%LOCALAPPDATA%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache"),
]

_UPDATE_RESIDUE_TARGETS = [
    ("SoftwareDistribution-Download", r"%WINDIR%\SoftwareDistribution\Download"),
    ("Windows-Installer-Cache", r"%WINDIR%\Installer\$PatchCache$"),
    ("Delivery-Optimization", r"%WINDIR%\SoftwareDistribution\DeliveryOptimization"),
    ("Package-Cache", r"%ProgramData%\Package Cache"),
]

_TELEMETRY_LOG_TARGETS = [
    ("WER-ReportQueue", r"%ProgramData%\Microsoft\Windows\WER\ReportQueue"),
    ("WER-ReportArchive", r"%ProgramData%\Microsoft\Windows\WER\ReportArchive"),
    ("WER-User-Queue", r"%LOCALAPPDATA%\Microsoft\Windows\WER\ReportQueue"),
    ("CBS-Logs", r"%WINDIR%\Logs\CBS"),
    ("Windows-Temp", r"%WINDIR%\Temp"),
    ("User-Temp", r"%LOCALAPPDATA%\Temp"),
]

_CATEGORY_MAP = {
    CATEGORY_CLOUD_SYNC: _CLOUD_SYNC_TARGETS,
    CATEGORY_BROWSER_CACHE: _BROWSER_CACHE_TARGETS,
    CATEGORY_UPDATE_RESIDUE: _UPDATE_RESIDUE_TARGETS,
    CATEGORY_TELEMETRY_LOG: _TELEMETRY_LOG_TARGETS,
}


def _resolve_targets(
    category: str,
    definitions: list[tuple[str, str]],
    include_missing: bool,
) -> list[TargetRoot]:
    roots: list[TargetRoot] = []
    seen: set[str] = set()

    for name, template in definitions:
        # Handle simple wildcard for OneDrive commercial folders
        if "*" in template:
            parent_template, _, _ = template.rpartition("\\")
            parent = _expand(parent_template)
            if parent.exists():
                try:
                    for child in parent.iterdir():
                        if child.is_dir() and child.name.startswith("OneDrive -"):
                            key = str(child).lower()
                            if key not in seen:
                                seen.add(key)
                                roots.append(TargetRoot(child.name, category, child, True))
                except OSError:
                    pass
            continue

        path = _expand(template)
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)

        exists = path.exists()
        if exists or include_missing:
            roots.append(TargetRoot(name, category, path, exists))

    return roots


def get_targets_for_category(
    category: str,
    *,
    include_missing: bool = False,
) -> list[TargetRoot]:
    """
    Get well-known target roots for a single detector category.

    Args:
        category: One of the CATEGORY_* constants.
        include_missing: If True, include roots that don't exist on disk.

    Returns:
        List of TargetRoot entries.

    Raises:
        ValueError: If category is not recognized.
    """
    if category not in _CATEGORY_MAP:
        raise ValueError(
            f"Unknown category: {category!r}. Valid: {', '.join(ALL_CATEGORIES)}"
        )
    return _resolve_targets(category, _CATEGORY_MAP[category], include_missing)


def get_all_targets(*, include_missing: bool = False) -> list[TargetRoot]:
    """Get well-known target roots across all detector categories."""
    result: list[TargetRoot] = []
    for category in ALL_CATEGORIES:
        result.extend(get_targets_for_category(category, include_missing=include_missing))
    return result


def get_cloud_sync_roots(*, include_missing: bool = False) -> list[TargetRoot]:
    """Cloud-sync targets (spec 4.4)."""
    return get_targets_for_category(CATEGORY_CLOUD_SYNC, include_missing=include_missing)


def get_browser_cache_roots(*, include_missing: bool = False) -> list[TargetRoot]:
    """Browser/WebView2 cache targets (spec 4.5)."""
    return get_targets_for_category(CATEGORY_BROWSER_CACHE, include_missing=include_missing)


def get_update_residue_roots(*, include_missing: bool = False) -> list[TargetRoot]:
    """Update/installer residue targets (spec 4.6)."""
    return get_targets_for_category(CATEGORY_UPDATE_RESIDUE, include_missing=include_missing)


def get_telemetry_log_roots(*, include_missing: bool = False) -> list[TargetRoot]:
    """Telemetry/log churn targets (spec 4.7)."""
    return get_targets_for_category(CATEGORY_TELEMETRY_LOG, include_missing=include_missing)
