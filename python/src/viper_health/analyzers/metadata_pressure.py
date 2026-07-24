"""
Composite metadata-pressure analyzer (spec Section 4.3).

Combines multiple metadata-stress signals into a single composite assessment:
- tiny-file totals
- directory counts
- MFT size
- MFT fragmentation
- growth velocity (optional, snapshot-over-snapshot)

Pure and testable: accepts already-collected metrics rather than performing I/O.

Default thresholds (spec 4.3):
- MFT size > 2.5 GiB
- MFT fragments > 10
- tiny files > 500,000
- directories > 200,000
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetadataPressureThresholds:
    """Thresholds for composite metadata pressure signals."""

    mft_size_gib_critical: float = 2.5
    mft_size_gib_warning: float = 2.0
    mft_fragments_critical: int = 10
    mft_fragments_warning: int = 5
    tiny_files_critical: int = 500_000
    tiny_files_warning: int = 250_000
    directories_critical: int = 200_000
    directories_warning: int = 100_000
    # Growth velocity (tiny files added per day)
    growth_per_day_critical: int = 25_000
    growth_per_day_warning: int = 10_000


@dataclass(frozen=True)
class PressureSignal:
    """A single contributing metadata-pressure signal."""

    name: str
    value: float
    warning_threshold: float
    critical_threshold: float
    severity: str  # "good" | "warning" | "critical"


@dataclass(frozen=True)
class MetadataPressureReport:
    """Composite metadata-pressure assessment."""

    signals: tuple[PressureSignal, ...]
    overall_severity: str
    pressure_score: int  # 0-100, higher = more pressure
    warning_count: int
    critical_count: int


def _classify_signal(
    name: str,
    value: float,
    warning: float,
    critical: float,
) -> PressureSignal:
    if value >= critical:
        severity = "critical"
    elif value >= warning:
        severity = "warning"
    else:
        severity = "good"
    return PressureSignal(name, value, warning, critical, severity)


def analyze_metadata_pressure(
    *,
    tiny_files_total: int,
    directories_total: int,
    mft_size_bytes: int | None = None,
    mft_fragments: int | None = None,
    tiny_files_growth_per_day: float | None = None,
    thresholds: MetadataPressureThresholds | None = None,
) -> MetadataPressureReport:
    """
    Compute composite metadata pressure from collected signals.

    Args:
        tiny_files_total: Total tiny files observed in scope.
        directories_total: Total directories scanned in scope.
        mft_size_bytes: Optional MFT size in bytes.
        mft_fragments: Optional MFT fragment count.
        tiny_files_growth_per_day: Optional churn velocity for tiny files.
        thresholds: Optional threshold overrides.

    Returns:
        MetadataPressureReport with per-signal classification and composite score.
    """
    if thresholds is None:
        thresholds = MetadataPressureThresholds()

    signals: list[PressureSignal] = []

    signals.append(
        _classify_signal(
            "tiny_files_total",
            tiny_files_total,
            thresholds.tiny_files_warning,
            thresholds.tiny_files_critical,
        )
    )
    signals.append(
        _classify_signal(
            "directories_total",
            directories_total,
            thresholds.directories_warning,
            thresholds.directories_critical,
        )
    )

    if mft_size_bytes is not None:
        mft_size_gib = mft_size_bytes / (1024**3)
        signals.append(
            _classify_signal(
                "mft_size_gib",
                round(mft_size_gib, 3),
                thresholds.mft_size_gib_warning,
                thresholds.mft_size_gib_critical,
            )
        )

    if mft_fragments is not None:
        signals.append(
            _classify_signal(
                "mft_fragments",
                mft_fragments,
                thresholds.mft_fragments_warning,
                thresholds.mft_fragments_critical,
            )
        )

    if tiny_files_growth_per_day is not None:
        signals.append(
            _classify_signal(
                "tiny_files_growth_per_day",
                round(tiny_files_growth_per_day, 1),
                thresholds.growth_per_day_warning,
                thresholds.growth_per_day_critical,
            )
        )

    warning_count = sum(1 for s in signals if s.severity == "warning")
    critical_count = sum(1 for s in signals if s.severity == "critical")

    if critical_count:
        overall = "critical"
    elif warning_count:
        overall = "warning"
    else:
        overall = "good"

    # Composite pressure score: weight critical signals heavily
    total_signals = len(signals) if signals else 1
    weighted = (critical_count * 100 + warning_count * 50) / total_signals
    pressure_score = min(100, int(round(weighted)))

    return MetadataPressureReport(
        signals=tuple(signals),
        overall_severity=overall,
        pressure_score=pressure_score,
        warning_count=warning_count,
        critical_count=critical_count,
    )
