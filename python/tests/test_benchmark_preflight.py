"""Tests for fail-closed active benchmark preflight."""

from viper_health.analyzers.benchmark_preflight import evaluate_benchmark_preflight
from viper_health.collectors.smart_data import DriveHealth
from viper_health.collectors.windows_events import EventLogSnapshot, WindowsEvent


def _snapshot(*events, available=True):
    return EventLogSnapshot(
        available=available,
        lookback_days=30,
        query_start_utc="2026-06-25T00:00:00Z",
        collected_at_utc="2026-07-25T00:00:00Z",
        log_oldest_utc="2026-04-01T00:00:00Z",
        log_newest_utc="2026-07-25T00:00:00Z",
        log_record_count=100,
        events=events,
        error=None if available else "denied",
    )


def _drive(**overrides):
    values = {
        "device_id": "0",
        "friendly_name": "Stable SSD",
        "media_type": "SSD",
        "health_status": "Healthy",
        "temperature_c": 40.0,
        "wear_percent": 5.0,
        "power_on_hours": 100,
        "read_errors_total": 0,
        "write_errors_total": 0,
        "severity": "good",
        "bus_type": "NVMe",
        "reliability_available": True,
        "read_latency_max_ms": 10.0,
        "write_latency_max_ms": 10.0,
    }
    values.update(overrides)
    return DriveHealth(**values)


def test_preflight_allows_complete_clean_evidence():
    result = evaluate_benchmark_preflight(_snapshot(), [_drive()])

    assert result.allowed is True
    assert result.reasons == ()


def test_preflight_blocks_storage_events():
    event = WindowsEvent(
        record_id=1,
        timestamp_utc="2026-07-01T00:00:00Z",
        provider="storahci",
        event_id=129,
        level="Warning",
        message="reset",
        properties=(),
    )

    result = evaluate_benchmark_preflight(_snapshot(event), [_drive()])

    assert result.allowed is False
    assert any("storage" in reason for reason in result.reasons)


def test_preflight_blocks_drive_errors_and_missing_reliability():
    result = evaluate_benchmark_preflight(
        _snapshot(),
        [
            _drive(
                friendly_name="Suspect SSD",
                severity="critical",
                reliability_available=False,
                read_errors_total=13,
            )
        ],
    )

    assert result.allowed is False
    assert any("13 read error" in reason for reason in result.reasons)
    assert any("reliability counters" in reason for reason in result.reasons)


def test_preflight_fails_closed_when_coverage_missing():
    result = evaluate_benchmark_preflight(_snapshot(available=False), [])

    assert result.allowed is False
    assert "Windows System event coverage is unavailable" in result.reasons
    assert "Physical-drive health and reliability data is unavailable" in result.reasons
