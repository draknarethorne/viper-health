"""Passive Windows System event-log collection for hardware health evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from viper_health.utils.windows_powershell import run_powershell_json


RELEVANT_EVENT_IDS = (
    1,
    7,
    17,
    18,
    19,
    20,
    41,
    46,
    47,
    51,
    55,
    98,
    129,
    140,
    153,
    157,
    1001,
    1101,
    1201,
    4101,
    6008,
)

RELEVANT_PROVIDERS = (
    "disk",
    "Display",
    "EventLog",
    "Microsoft-Windows-Display-Driver",
    "Microsoft-Windows-Kernel-Power",
    "Microsoft-Windows-MemoryDiagnostics-Results",
    "Microsoft-Windows-Ntfs",
    "Microsoft-Windows-WER-SystemErrorReporting",
    "Microsoft-Windows-WHEA-Logger",
    "Ntfs",
    "storahci",
    "stornvme",
)


@dataclass(frozen=True)
class WindowsEvent:
    """Normalized event record independent of localized message text."""

    record_id: int | None
    timestamp_utc: str
    provider: str
    event_id: int
    level: str
    message: str
    properties: tuple[str, ...]


@dataclass(frozen=True)
class EventLogSnapshot:
    """System-log query result including coverage and availability metadata."""

    available: bool
    lookback_days: int
    query_start_utc: str | None
    collected_at_utc: str | None
    log_oldest_utc: str | None
    log_newest_utc: str | None
    log_record_count: int | None
    events: tuple[WindowsEvent, ...]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable representation."""
        return {
            "available": self.available,
            "lookback_days": self.lookback_days,
            "query_start_utc": self.query_start_utc,
            "collected_at_utc": self.collected_at_utc,
            "log_oldest_utc": self.log_oldest_utc,
            "log_newest_utc": self.log_newest_utc,
            "log_record_count": self.log_record_count,
            "event_count": len(self.events),
            "events": [asdict(event) for event in self.events],
            "error": self.error,
        }


def _as_records(value: object) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _to_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def collect_system_events(*, lookback_days: int = 90) -> EventLogSnapshot:
    """Collect relevant storage, crash, WHEA, memory, and display events.

    Collection is read-only. Provider and event identifiers drive analysis so
    localized Windows message text is retained as evidence but is not required
    for primary classification.
    """
    if lookback_days < 1:
        raise ValueError("lookback_days must be at least 1")

    ids = ",".join(str(event_id) for event_id in RELEVANT_EVENT_IDS)
    providers = ",".join(f"'{provider}'" for provider in RELEVANT_PROVIDERS)
    script = rf"""
$ErrorActionPreference = 'Stop'
try {{
    $start = (Get-Date).AddDays(-{lookback_days})
    $ids = @({ids})
    $providers = @({providers})
    $log = Get-WinEvent -ListLog System
    $oldest = Get-WinEvent -LogName System -Oldest -MaxEvents 1 -ErrorAction SilentlyContinue
    $newest = Get-WinEvent -LogName System -MaxEvents 1 -ErrorAction SilentlyContinue
    $events = Get-WinEvent -FilterHashtable @{{LogName='System'; StartTime=$start; Id=$ids}} -ErrorAction SilentlyContinue |
        Where-Object {{ $providers -contains $_.ProviderName }} |
        Sort-Object TimeCreated |
        ForEach-Object {{
            [PSCustomObject]@{{
                RecordId = $_.RecordId
                TimestampUtc = $_.TimeCreated.ToUniversalTime().ToString('o')
                Provider = $_.ProviderName
                EventId = $_.Id
                Level = $_.LevelDisplayName
                Message = $_.Message
                Properties = @($_.Properties | ForEach-Object {{
                    if ($null -eq $_.Value) {{ '' }} else {{ [string]$_.Value }}
                }})
            }}
        }}
    [PSCustomObject]@{{
        Available = $true
        QueryStartUtc = $start.ToUniversalTime().ToString('o')
        CollectedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        LogOldestUtc = if ($oldest) {{ $oldest.TimeCreated.ToUniversalTime().ToString('o') }} else {{ $null }}
        LogNewestUtc = if ($newest) {{ $newest.TimeCreated.ToUniversalTime().ToString('o') }} else {{ $null }}
        LogRecordCount = $log.RecordCount
        Events = @($events)
        Error = $null
    }} | ConvertTo-Json -Depth 6 -Compress
}} catch {{
    [PSCustomObject]@{{
        Available = $false
        QueryStartUtc = $null
        CollectedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        LogOldestUtc = $null
        LogNewestUtc = $null
        LogRecordCount = $null
        Events = @()
        Error = $_.Exception.Message
    }} | ConvertTo-Json -Depth 4 -Compress
}}
"""
    result = run_powershell_json(script, timeout_seconds=120)
    if not result.available or not isinstance(result.data, dict):
        return EventLogSnapshot(
            available=False,
            lookback_days=lookback_days,
            query_start_utc=None,
            collected_at_utc=None,
            log_oldest_utc=None,
            log_newest_utc=None,
            log_record_count=None,
            events=(),
            error=result.error or "Windows event data was unavailable",
        )

    payload = result.data
    events: list[WindowsEvent] = []
    for record in _as_records(payload.get("Events")):
        event_id = _to_int(record.get("EventId"))
        if event_id is None:
            continue
        raw_properties = record.get("Properties")
        if isinstance(raw_properties, list):
            properties = tuple(str(value) for value in raw_properties)
        elif raw_properties is None:
            properties = ()
        else:
            properties = (str(raw_properties),)
        events.append(
            WindowsEvent(
                record_id=_to_int(record.get("RecordId")),
                timestamp_utc=str(record.get("TimestampUtc") or ""),
                provider=str(record.get("Provider") or "Unknown"),
                event_id=event_id,
                level=str(record.get("Level") or "Unknown"),
                message=str(record.get("Message") or ""),
                properties=properties,
            )
        )

    available = bool(payload.get("Available", True))
    return EventLogSnapshot(
        available=available,
        lookback_days=lookback_days,
        query_start_utc=str(payload.get("QueryStartUtc") or "") or None,
        collected_at_utc=str(payload.get("CollectedAtUtc") or "") or None,
        log_oldest_utc=str(payload.get("LogOldestUtc") or "") or None,
        log_newest_utc=str(payload.get("LogNewestUtc") or "") or None,
        log_record_count=_to_int(payload.get("LogRecordCount")),
        events=tuple(events),
        error=str(payload.get("Error") or "") or None,
    )
