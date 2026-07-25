"""Markdown rendering for comprehensive system-health evidence reports."""

from __future__ import annotations

from typing import Any


_SEVERITY_ICON = {
    "critical": "CRITICAL",
    "warning": "WARNING",
    "good": "GOOD",
    "info": "INFO",
    "unknown": "UNKNOWN",
}


def _escape(value: object, *, limit: int = 220) -> str:
    if value is None or value == "":
        text = "Unknown"
    else:
        text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def _bytes_gib(value: object) -> str:
    try:
        return f"{int(value) / (1024**3):,.2f} GiB"
    except (TypeError, ValueError):
        return "Unknown"


def build_system_health_markdown(report: dict[str, Any]) -> str:
    """Render a comprehensive JSON report as AI-friendly Markdown."""
    assessment = report["assessment"]
    lines = [
        "# Viper Health Comprehensive System Report",
        "",
        "## Report identity",
        "",
        f"- **Host:** `{_escape(report.get('host'))}`",
        f"- **Generated (UTC):** {report.get('timestamp_utc', 'Unknown')}",
        f"- **Schema:** {report.get('schema_version', 'Unknown')}",
        f"- **Mode:** {report.get('mode', 'observe')}",
        f"- **Event lookback:** {report.get('event_lookback_days', 0)} days",
        "",
        "## Overall assessment",
        "",
        f"- **Severity:** {_SEVERITY_ICON.get(assessment['severity'], assessment['severity'].upper())}",
        f"- **Confidence:** {assessment['confidence'].upper()}",
        f"- **Conclusion:** {assessment['conclusion']}",
        "",
        "> This is an evidence report, not a warranty of hardware health. Missing or",
        "> inaccessible data remains UNKNOWN and never becomes a green result.",
        "",
    ]

    inventory = report.get("system_inventory", {})
    lines.extend(["## Machine specifications", ""])
    if inventory.get("available"):
        system = inventory.get("ComputerSystem") or {}
        os_info = inventory.get("OperatingSystem") or {}
        board = inventory.get("Baseboard") or {}
        bios = inventory.get("Bios") or {}
        lines.extend(
            [
                f"- **System:** {_escape(system.get('Manufacturer'))} {_escape(system.get('Model'))}",
                f"- **Motherboard:** {_escape(board.get('Manufacturer'))} {_escape(board.get('Product'))} rev {_escape(board.get('Version'))}",
                f"- **BIOS:** {_escape(bios.get('Manufacturer'))} {_escape(bios.get('SMBIOSVersion'))} ({_escape(bios.get('ReleaseDateUtc'))})",
                f"- **OS:** {_escape(os_info.get('Caption'))} build {_escape(os_info.get('BuildNumber'))}",
                f"- **Last boot:** {_escape(os_info.get('LastBootUtc'))}",
                f"- **Installed memory:** {_bytes_gib(system.get('TotalPhysicalMemoryBytes'))}",
                f"- **Free memory at collection:** {_bytes_gib((os_info.get('FreePhysicalMemoryKb') or 0) * 1024)}",
                f"- **Secure Boot:** {_escape(inventory.get('SecureBootEnabled'))}",
                "",
            ]
        )
        cpus = inventory.get("Cpu") or []
        if isinstance(cpus, dict):
            cpus = [cpus]
        lines.extend(["### CPU", "", "| Name | Cores / Threads | Clock | Load | Status |", "| --- | ---: | ---: | ---: | --- |"])
        for cpu in cpus:
            lines.append(
                f"| {_escape(cpu.get('Name'))} | {cpu.get('Cores', '?')} / {cpu.get('LogicalProcessors', '?')} | "
                f"{cpu.get('CurrentClockMhz', '?')} / {cpu.get('MaxClockMhz', '?')} MHz | "
                f"{cpu.get('LoadPercent', '?')}% | {_escape(cpu.get('Status'))} |"
            )
        lines.append("")

        modules = inventory.get("MemoryModules") or []
        if isinstance(modules, dict):
            modules = [modules]
        lines.extend(["### Memory modules", "", "| Locator | Capacity | Configured speed | Manufacturer / Part |", "| --- | ---: | ---: | --- |"])
        for module in modules:
            lines.append(
                f"| {_escape(module.get('DeviceLocator') or module.get('BankLabel'))} | "
                f"{_bytes_gib(module.get('CapacityBytes'))} | {module.get('ConfiguredSpeedMhz') or module.get('SpeedMhz') or '?'} MHz | "
                f"{_escape(module.get('Manufacturer'))} {_escape(module.get('PartNumber'))} |"
            )
        lines.append("")

        gpus = inventory.get("Gpus") or []
        if isinstance(gpus, dict):
            gpus = [gpus]
        lines.extend(["### Graphics", "", "| Device | Driver | Adapter RAM | Status |", "| --- | --- | ---: | --- |"])
        for gpu in gpus:
            lines.append(
                f"| {_escape(gpu.get('Name'))} | {_escape(gpu.get('DriverVersion'))} | "
                f"{_bytes_gib(gpu.get('AdapterRamBytes'))} | {_escape(gpu.get('Status'))} |"
            )
        lines.append("")
    else:
        lines.extend([f"System inventory unavailable: {_escape(inventory.get('error'))}", ""])

    findings = report.get("findings", [])
    lines.extend(["## Findings", ""])
    if findings:
        lines.extend(["| Severity | Domain | Evidence | Confidence |", "| --- | --- | ---: | --- |"])
        for finding in findings:
            lines.append(
                f"| {finding.get('severity', 'unknown').upper()} | {_escape(finding.get('domain'))} | "
                f"{finding.get('event_count', finding.get('evidence_count', 1))} | "
                f"{finding.get('confidence', 'medium').upper()} |"
            )
        lines.append("")
        for finding in findings:
            lines.extend(
                [
                    f"### {finding.get('severity', 'unknown').upper()}: {finding.get('title', finding.get('domain', 'Finding'))}",
                    "",
                    finding.get("summary", "No summary available."),
                    "",
                    f"**Recommendation:** {finding.get('recommendation', 'Review the underlying evidence.')}",
                    "",
                ]
            )
    else:
        lines.extend(["No fault findings were detected in the evidence that was successfully collected.", ""])

    storage = report.get("storage", {})
    lines.extend(["## Storage evidence", ""])
    drives = storage.get("drives")
    if isinstance(drives, list) and drives:
        lines.extend(
            [
                "| Disk | Bus / Media | Summary | Temperature | Wear | Read / Write errors | Max read / write latency |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for drive in drives:
            lines.append(
                f"| {_escape(drive.get('friendly_name'))} | {_escape(drive.get('bus_type'))} / {_escape(drive.get('media_type'))} | "
                f"{_escape(drive.get('health_status'))} ({_escape(drive.get('severity'))}) | "
                f"{drive.get('temperature_c', '?')} C | {drive.get('wear_percent', '?')}% | "
                f"{drive.get('read_errors_total', '?')} / {drive.get('write_errors_total', '?')} | "
                f"{drive.get('read_latency_max_ms', '?')} / {drive.get('write_latency_max_ms', '?')} ms |"
            )
        lines.append("")
    elif isinstance(drives, dict):
        lines.extend([f"Drive data unavailable: {_escape(drives.get('error'))}", ""])
    else:
        lines.extend(["No physical-drive records were returned.", ""])

    for label, key in (("Disk space", "disk_space"), ("TRIM", "trim"), ("MFT", "mft")):
        value = storage.get(key)
        if value is not None:
            lines.append(f"- **{label}:** `{_escape(value, limit=500)}`")
    lines.append("")

    event_log = report.get("event_log", {})
    event_analysis = report.get("event_analysis", {})
    lines.extend(
        [
            "## Windows event evidence",
            "",
            f"- **Collection available:** {event_log.get('available', False)}",
            f"- **Log coverage:** {event_log.get('log_oldest_utc') or 'Unknown'} through {event_log.get('log_newest_utc') or 'Unknown'}",
            f"- **Query start:** {event_log.get('query_start_utc') or 'Unknown'}",
            f"- **Matching events:** {event_log.get('event_count', 0)}",
            f"- **Event assessment:** {event_analysis.get('overall_severity', 'unknown').upper()}",
            "",
        ]
    )
    events = event_log.get("events") or []
    if events:
        lines.extend(["### Most recent matching events", "", "| Time (UTC) | Provider | ID | Level | Message |", "| --- | --- | ---: | --- | --- |"])
        for event in reversed(events[-50:]):
            lines.append(
                f"| {_escape(event.get('timestamp_utc'))} | {_escape(event.get('provider'))} | "
                f"{event.get('event_id', '?')} | {_escape(event.get('level'))} | {_escape(event.get('message'))} |"
            )
        lines.append("")

    filesystem = report.get("filesystem")
    if filesystem is not None:
        lines.extend(["## Filesystem pressure", "", f"`{_escape(filesystem, limit=1000)}`", ""])

    lines.extend(["## Collection status", "", "| Section | Available | Error / limitation |", "| --- | --- | --- |"])
    for name, status in report.get("collection_status", {}).items():
        lines.append(
            f"| {_escape(name)} | {status.get('available', False)} | {_escape(status.get('error'))} |"
        )
    lines.append("")

    lines.extend(["## Recommendations", ""])
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    lines.extend(
        [
            "",
            "## AI review guidance",
            "",
            "When evaluating this report, prioritize concrete event and error evidence over",
            "summary labels. Correlate timestamps across domains, distinguish absent evidence",
            "from unavailable collection, and do not recommend stress tests when storage, WHEA,",
            "memory, power, or crash evidence is unresolved.",
            "",
        ]
    )
    return "\n".join(lines)
