"""Safety gate for active benchmarks based on passive health evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from viper_health.analyzers.system_events import analyze_system_events
from viper_health.collectors.smart_data import DriveHealth, get_drive_health
from viper_health.collectors.windows_events import EventLogSnapshot, collect_system_events


@dataclass(frozen=True)
class BenchmarkPreflight:
    """Decision and evidence for whether active I/O testing is allowed."""

    allowed: bool
    lookback_days: int
    reasons: tuple[str, ...]
    event_severity: str
    matching_event_count: int
    drives_checked: int
    drive_summaries: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_benchmark_preflight(
    snapshot: EventLogSnapshot,
    drives: list[DriveHealth],
) -> BenchmarkPreflight:
    """Return a fail-closed benchmark decision from events and drive facts."""
    reasons: list[str] = []
    analysis = analyze_system_events(snapshot)

    if not snapshot.available:
        reasons.append("Windows System event coverage is unavailable")
    else:
        for finding in analysis.findings:
            if finding.severity in {"warning", "critical"}:
                reasons.append(
                    f"{finding.domain}: {finding.event_count} relevant event(s) "
                    f"({finding.severity})"
                )

    if not drives:
        reasons.append("Physical-drive health and reliability data is unavailable")

    summaries: list[dict[str, Any]] = []
    for drive in drives:
        summaries.append(
            {
                "device_id": drive.device_id,
                "friendly_name": drive.friendly_name,
                "bus_type": drive.bus_type,
                "health_status": drive.health_status,
                "severity": drive.severity,
                "reliability_available": drive.reliability_available,
                "read_errors_total": drive.read_errors_total,
                "write_errors_total": drive.write_errors_total,
                "read_latency_max_ms": drive.read_latency_max_ms,
                "write_latency_max_ms": drive.write_latency_max_ms,
            }
        )
        name = drive.friendly_name or f"Disk {drive.device_id}"
        if drive.severity in {"warning", "critical", "unknown"}:
            reasons.append(f"{name}: drive severity is {drive.severity}")
        if not drive.reliability_available:
            reasons.append(f"{name}: reliability counters are unavailable")
        if (drive.read_errors_total or 0) > 0:
            reasons.append(f"{name}: {drive.read_errors_total} read error(s) reported")
        if (drive.write_errors_total or 0) > 0:
            reasons.append(f"{name}: {drive.write_errors_total} write error(s) reported")

    # Preserve order while removing duplicate reasons.
    unique_reasons = tuple(dict.fromkeys(reasons))
    return BenchmarkPreflight(
        allowed=not unique_reasons,
        lookback_days=snapshot.lookback_days,
        reasons=unique_reasons,
        event_severity=analysis.overall_severity,
        matching_event_count=len(snapshot.events),
        drives_checked=len(drives),
        drive_summaries=tuple(summaries),
    )


def run_benchmark_preflight(*, lookback_days: int = 30) -> BenchmarkPreflight:
    """Collect passive evidence and fail closed before any benchmark writes."""
    snapshot = collect_system_events(lookback_days=lookback_days)
    try:
        drives = get_drive_health()
    except Exception:
        drives = []
    return evaluate_benchmark_preflight(snapshot, drives)
