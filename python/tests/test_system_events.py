"""Tests for Windows hardware and stability event analysis."""

from viper_health.analyzers.system_events import analyze_system_events
from viper_health.collectors.windows_events import EventLogSnapshot, WindowsEvent


def _event(provider, event_id, record_id, timestamp, message=""):
    return WindowsEvent(
        record_id=record_id,
        timestamp_utc=timestamp,
        provider=provider,
        event_id=event_id,
        level="Warning",
        message=message,
        properties=(),
    )


def _snapshot(*events, available=True):
    return EventLogSnapshot(
        available=available,
        lookback_days=90,
        query_start_utc="2026-04-01T00:00:00Z",
        collected_at_utc="2026-07-01T00:00:00Z",
        log_oldest_utc="2026-03-01T00:00:00Z",
        log_newest_utc="2026-07-01T00:00:00Z",
        log_record_count=100,
        events=events,
        error=None if available else "denied",
    )


def test_analysis_marks_repeated_storage_resets_critical():
    analysis = analyze_system_events(
        _snapshot(
            _event("storahci", 129, 1, "2026-05-01T00:00:00Z"),
            _event("disk", 153, 2, "2026-06-01T00:00:00Z"),
        )
    )

    assert analysis.overall_severity == "critical"
    finding = analysis.findings[0]
    assert finding.domain == "storage"
    assert finding.event_count == 2
    assert finding.event_ids == (129, 153)
    assert finding.record_ids == (1, 2)


def test_analysis_marks_bugcheck_critical():
    analysis = analyze_system_events(
        _snapshot(
            _event(
                "Microsoft-Windows-WER-SystemErrorReporting",
                1001,
                3,
                "2026-06-01T00:00:00Z",
            )
        )
    )

    assert analysis.overall_severity == "critical"
    assert analysis.findings[0].domain == "system_stability"


def test_analysis_distinguishes_corrected_and_fatal_whea():
    corrected = analyze_system_events(
        _snapshot(
            _event("Microsoft-Windows-WHEA-Logger", 19, 4, "2026-06-01T00:00:00Z")
        )
    )
    fatal = analyze_system_events(
        _snapshot(
            _event("Microsoft-Windows-WHEA-Logger", 18, 5, "2026-06-01T00:00:00Z")
        )
    )

    assert corrected.overall_severity == "warning"
    assert corrected.findings[0].confidence == "medium"
    assert fatal.overall_severity == "critical"
    assert fatal.findings[0].confidence == "high"


def test_analysis_does_not_call_clean_memory_result_a_fault():
    analysis = analyze_system_events(
        _snapshot(
            _event(
                "Microsoft-Windows-MemoryDiagnostics-Results",
                1201,
                6,
                "2026-06-01T00:00:00Z",
                "The Windows Memory Diagnostic tested memory and detected no errors.",
            )
        )
    )

    assert analysis.overall_severity == "info"
    assert analysis.findings[0].severity == "info"


def test_analysis_does_not_call_unlocalized_memory_result_a_fault():
    analysis = analyze_system_events(
        _snapshot(
            _event(
                "Microsoft-Windows-MemoryDiagnostics-Results",
                1201,
                7,
                "2026-06-01T00:00:00Z",
                "Résultat du diagnostic de mémoire.",
            )
        )
    )

    assert analysis.overall_severity == "info"
    assert analysis.findings[0].confidence == "low"


def test_analysis_reports_unavailable_coverage_as_unknown():
    analysis = analyze_system_events(_snapshot(available=False))

    assert analysis.overall_severity == "unknown"
    assert analysis.coverage_status == "unavailable"
    assert analysis.findings == ()
