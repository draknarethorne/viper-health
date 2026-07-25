"""Pure analysis of Windows hardware and stability event evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from viper_health.collectors.windows_events import EventLogSnapshot, WindowsEvent


SEVERITY_ORDER = {"unknown": -1, "info": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class EventFinding:
    """Aggregated evidence for one health domain."""

    domain: str
    severity: str
    confidence: str
    title: str
    event_count: int
    event_ids: tuple[int, ...]
    providers: tuple[str, ...]
    first_seen_utc: str | None
    last_seen_utc: str | None
    record_ids: tuple[int, ...]
    summary: str
    recommendation: str


@dataclass(frozen=True)
class SystemEventAnalysis:
    """Classified event evidence with explicit collection coverage."""

    overall_severity: str
    coverage_status: str
    findings: tuple[EventFinding, ...]
    domain_event_counts: dict[str, int]
    unclassified_event_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_severity": self.overall_severity,
            "coverage_status": self.coverage_status,
            "finding_count": len(self.findings),
            "domain_event_counts": self.domain_event_counts,
            "unclassified_event_count": self.unclassified_event_count,
            "findings": [asdict(finding) for finding in self.findings],
        }


def _domain_for(event: WindowsEvent) -> str | None:
    provider = event.provider.casefold()
    if "whea-logger" in provider:
        return "hardware_whea"
    if "memorydiagnostics" in provider:
        return "memory_diagnostics"
    if provider in {"storahci", "stornvme", "disk", "ntfs", "microsoft-windows-ntfs"}:
        return "storage"
    if provider in {
        "microsoft-windows-kernel-power",
        "eventlog",
        "microsoft-windows-wer-systemerrorreporting",
    } and event.event_id in {41, 1001, 6008}:
        return "system_stability"
    if provider in {"display", "microsoft-windows-display-driver"}:
        return "display_driver"
    return None


def _memory_error_detected(events: list[WindowsEvent]) -> bool:
    text = " ".join(event.message.casefold() for event in events)
    return any(
        phrase in text
        for phrase in (
            "hardware problems were detected",
            "memory errors were detected",
            "detected hardware errors",
        )
    )


def _classify(domain: str, events: list[WindowsEvent]) -> tuple[str, str, str, str, str]:
    ids = {event.event_id for event in events}
    count = len(events)

    if domain == "storage":
        hard_fault_ids = {7, 51, 55, 98, 140, 157}
        severity = "critical" if ids & hard_fault_ids or count >= 2 else "warning"
        return (
            severity,
            "high",
            "Storage path errors or resets detected",
            f"Windows recorded {count} storage/controller event(s); concrete I/O evidence overrides green summary status.",
            "Back up data, avoid stress tests, inspect per-disk evidence, and isolate the drive/cable/port/power path.",
        )

    if domain == "system_stability":
        bugchecks = sum(event.event_id == 1001 for event in events)
        severity = "critical" if bugchecks or count >= 2 else "warning"
        return (
            severity,
            "high",
            "Unexpected shutdown or bugcheck evidence detected",
            f"Windows recorded {count} stability event(s), including {bugchecks} bugcheck report(s).",
            "Correlate timestamps with WHEA, storage, memory, and display findings before changing hardware.",
        )

    if domain == "hardware_whea":
        uncorrected = ids & {1, 18, 20, 46, 47}
        severity = "critical" if uncorrected else "warning"
        confidence = "high" if uncorrected else "medium"
        return (
            severity,
            confidence,
            "Windows hardware error architecture events detected",
            f"Windows recorded {count} WHEA event(s); IDs were {', '.join(str(value) for value in sorted(ids))}.",
            "Inspect event details for CPU/cache, memory, PCIe, or device identity and track recurrence by component.",
        )

    if domain == "memory_diagnostics":
        fault = _memory_error_detected(events)
        severity = "critical" if fault else "info"
        return (
            severity,
            "high" if fault else "low",
            "Windows Memory Diagnostic results available",
            "Memory diagnostic output explicitly indicates a fault." if fault else "No language-independent fault classification was possible from this result.",
            "If a fault is reported, stop stress testing and validate DIMMs individually after storage is stable." if fault else "Retain this result as evidence; absence of an event is not a memory test.",
        )

    return (
        "warning",
        "medium",
        "Display driver recovery events detected",
        f"Windows recorded {count} display-driver reset/recovery event(s).",
        "Update or clean-install the GPU driver and correlate recurrence with GPU load, temperature, power, and WHEA events.",
    )


def analyze_system_events(snapshot: EventLogSnapshot) -> SystemEventAnalysis:
    """Classify a passive event-log snapshot into evidence-based findings."""
    if not snapshot.available:
        return SystemEventAnalysis(
            overall_severity="unknown",
            coverage_status="unavailable",
            findings=(),
            domain_event_counts={},
            unclassified_event_count=0,
        )

    grouped: dict[str, list[WindowsEvent]] = {}
    unclassified = 0
    for event in snapshot.events:
        domain = _domain_for(event)
        if domain is None:
            unclassified += 1
            continue
        grouped.setdefault(domain, []).append(event)

    findings: list[EventFinding] = []
    for domain, events in grouped.items():
        severity, confidence, title, summary, recommendation = _classify(domain, events)
        timestamps = sorted(event.timestamp_utc for event in events if event.timestamp_utc)
        record_ids = tuple(
            event.record_id for event in events if event.record_id is not None
        )
        findings.append(
            EventFinding(
                domain=domain,
                severity=severity,
                confidence=confidence,
                title=title,
                event_count=len(events),
                event_ids=tuple(sorted({event.event_id for event in events})),
                providers=tuple(sorted({event.provider for event in events})),
                first_seen_utc=timestamps[0] if timestamps else None,
                last_seen_utc=timestamps[-1] if timestamps else None,
                record_ids=record_ids,
                summary=summary,
                recommendation=recommendation,
            )
        )

    findings.sort(
        key=lambda finding: (
            -SEVERITY_ORDER.get(finding.severity, -1),
            finding.domain,
        )
    )
    overall = max(
        (finding.severity for finding in findings),
        key=lambda severity: SEVERITY_ORDER.get(severity, -1),
        default="info",
    )
    return SystemEventAnalysis(
        overall_severity=overall,
        coverage_status="available",
        findings=tuple(findings),
        domain_event_counts={domain: len(events) for domain, events in sorted(grouped.items())},
        unclassified_event_count=unclassified,
    )
