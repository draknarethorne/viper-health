"""Comprehensive passive Windows system-health report CLI."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from viper_health.analyzers.spec_assessment import assess_system_capability
from viper_health.analyzers.system_events import SEVERITY_ORDER, analyze_system_events
from viper_health.cli.scan import run_full_scan
from viper_health.collectors.disk_space import analyze_disk_space
from viper_health.collectors.mft_info import analyze_mft_health, get_mft_info
from viper_health.collectors.smart_data import get_drive_health, is_elevated
from viper_health.collectors.system_inventory import collect_system_inventory
from viper_health.collectors.trim_status import check_trim_status
from viper_health.collectors.volume_info import get_volume_info
from viper_health.collectors.windows_events import collect_system_events
from viper_health.reports.system_health_reporter import build_system_health_markdown


SCHEMA_VERSION = 1


def _status(value: object, error: str | None = None) -> dict[str, Any]:
    available = not isinstance(value, dict) or value.get("available", True) is not False
    return {"available": available, "error": error}


def _collect(
    name: str,
    collector: Callable[[], Any],
    *,
    empty_is_unavailable: bool = False,
) -> tuple[Any, dict[str, Any]]:
    try:
        value = collector()
        if empty_is_unavailable and isinstance(value, (list, tuple)) and not value:
            return value, {
                "available": False,
                "error": f"{name} returned no records",
            }
        if isinstance(value, dict) and value.get("available") is False:
            return value, _status(value, str(value.get("error") or "Unavailable"))
        return value, _status(value)
    except Exception as exc:  # environment/permission dependent
        unavailable = {"available": False, "error": str(exc)}
        return unavailable, _status(unavailable, str(exc))


def _add_drive_findings(drives: object, findings: list[dict[str, Any]]) -> None:
    if not isinstance(drives, list):
        return
    for drive in drives:
        severity = str(drive.get("severity", "unknown"))
        if severity not in {"warning", "critical"}:
            continue
        name = str(drive.get("friendly_name") or drive.get("device_id") or "Unknown disk")
        evidence = []
        for key, label in (
            ("read_errors_total", "read errors"),
            ("write_errors_total", "write errors"),
            ("read_latency_max_ms", "max read latency ms"),
            ("write_latency_max_ms", "max write latency ms"),
            ("temperature_c", "temperature C"),
            ("wear_percent", "wear percent"),
        ):
            value = drive.get(key)
            if value not in (None, 0, 0.0):
                evidence.append(f"{label}={value}")
        findings.append(
            {
                "domain": "storage_device",
                "severity": severity,
                "confidence": "high" if evidence else "medium",
                "title": f"Drive evidence requires attention: {name}",
                "evidence_count": len(evidence) or 1,
                "summary": (
                    f"Windows reports {drive.get('health_status', 'Unknown')} summary status, "
                    f"but the combined drive severity is {severity}. "
                    + ("Evidence: " + ", ".join(evidence) + "." if evidence else "")
                ),
                "recommendation": "Back up important data and correlate this disk with Windows storage events before any benchmark or stress test.",
            }
        )


def _add_section_finding(
    section: object,
    *,
    domain: str,
    severity_key: str,
    title: str,
    recommendation: str,
    findings: list[dict[str, Any]],
) -> None:
    if not isinstance(section, dict):
        return
    severity = str(section.get(severity_key, "unknown"))
    if severity not in {"warning", "critical"}:
        return
    findings.append(
        {
            "domain": domain,
            "severity": severity,
            "confidence": "high",
            "title": title,
            "evidence_count": 1,
            "summary": json.dumps(section, sort_keys=True),
            "recommendation": recommendation,
        }
    )


def _build_assessment(
    findings: list[dict[str, Any]],
    collection_status: dict[str, dict[str, Any]],
) -> dict[str, str]:
    severities = [str(finding.get("severity", "unknown")) for finding in findings]
    if severities:
        severity = max(
            severities,
            key=lambda value: SEVERITY_ORDER.get(value, -1),
        )
    else:
        severity = "good" if any(
            status.get("available") for status in collection_status.values()
        ) else "unknown"

    unavailable = [name for name, status in collection_status.items() if not status.get("available")]
    confidence = "high" if not unavailable else "medium" if len(unavailable) <= 2 else "low"
    if severity == "critical":
        conclusion = "Critical fault evidence was detected; resolve concrete errors before performance testing."
    elif severity == "warning":
        conclusion = "Warning evidence was detected and should be trended or investigated."
    elif severity == "good":
        conclusion = "No fault findings were detected in the evidence successfully collected."
    else:
        conclusion = "Insufficient evidence was collected to assess system health."
    if unavailable:
        conclusion += " Unavailable sections: " + ", ".join(unavailable) + "."
    return {"severity": severity, "confidence": confidence, "conclusion": conclusion}


def _recommendations(findings: list[dict[str, Any]], status: dict[str, dict[str, Any]]) -> list[str]:
    domains = {str(finding.get("domain")) for finding in findings}
    recommendations: list[str] = []
    if domains & {"storage", "storage_device"}:
        recommendations.append("Back up irreplaceable data and do not run storage benchmarks or write-heavy diagnostics until storage evidence is resolved.")
    if "system_stability" in domains:
        recommendations.append("Correlate each crash timestamp with storage, WHEA, memory, display, and power evidence; a Kernel-Power event alone does not identify the cause.")
    if "hardware_whea" in domains:
        recommendations.append("Inspect WHEA record details and recurrence by CPU/cache, memory, PCIe bus, and endpoint before replacing components.")
    if "memory_diagnostics" in domains:
        recommendations.append("Treat explicit memory-diagnostic failures as actionable; validate DIMMs individually only after storage is stable and backups are current.")
    if "display_driver" in domains:
        recommendations.append("Correlate display recoveries with GPU driver version, load, temperature, power, and WHEA evidence.")
    unavailable = [name for name, value in status.items() if not value.get("available")]
    if unavailable:
        recommendations.append("Re-run from an elevated PowerShell terminal to improve collection coverage for: " + ", ".join(unavailable) + ".")
    if not recommendations:
        recommendations.append("Retain this report as a baseline and compare future event counts and hardware facts after normal use.")
    recommendations.append("Use active benchmarks only on known-stable, backed-up hardware after passive preflight finds no unresolved fault evidence.")
    return recommendations


def build_system_health_report(
    *,
    lookback_days: int = 90,
    drive: str = "C:",
    include_events: bool = True,
    include_inventory: bool = True,
    include_storage: bool = True,
    include_volumes: bool = True,
    include_trim: bool = True,
    include_mft: bool = True,
    filesystem_root: Path | None = None,
    exclude_paths: list[str] | None = None,
    show_progress: bool = False,
) -> dict[str, Any]:
    """Build a versioned, JSON-serializable whole-machine evidence report."""
    timestamp = datetime.now(timezone.utc).isoformat()
    host = socket.gethostname()
    collection_status: dict[str, dict[str, Any]] = {}

    if include_inventory:
        inventory_obj = collect_system_inventory()
        inventory = inventory_obj.to_dict()
        collection_status["system_inventory"] = {
            "available": inventory_obj.available,
            "error": inventory_obj.error,
        }
    else:
        inventory = {"available": False, "error": "Skipped by operator"}
        collection_status["system_inventory"] = _status(inventory, "Skipped by operator")

    # Advisory capability assessment. Deliberately kept out of `findings` so it
    # never influences the fault-evidence severity.
    capability = assess_system_capability(inventory)

    if include_events:
        event_snapshot = collect_system_events(lookback_days=lookback_days)
        event_log = event_snapshot.to_dict()
        event_analysis_obj = analyze_system_events(event_snapshot)
        event_analysis = event_analysis_obj.to_dict()
        collection_status["event_log"] = {
            "available": event_snapshot.available,
            "error": event_snapshot.error,
        }
    else:
        event_log = {"available": False, "events": [], "event_count": 0, "error": "Skipped by operator"}
        event_analysis = {
            "overall_severity": "unknown",
            "coverage_status": "unavailable",
            "findings": [],
        }
        collection_status["event_log"] = _status(event_log, "Skipped by operator")

    storage: dict[str, Any] = {}
    if include_storage:
        drives, collection_status["physical_drives"] = _collect(
            "physical_drives",
            lambda: [asdict(drive_info) for drive_info in get_drive_health()],
            empty_is_unavailable=True,
        )
        storage["drives"] = drives
        space, collection_status["disk_space"] = _collect(
            "disk_space", lambda: asdict(analyze_disk_space(drive))
        )
        storage["disk_space"] = space
        try:
            storage["elevated"] = is_elevated()
        except Exception:
            storage["elevated"] = None

        if include_volumes:
            volumes, collection_status["volumes"] = _collect(
                "volumes",
                lambda: [asdict(volume) for volume in get_volume_info()],
                empty_is_unavailable=True,
            )
            storage["volumes"] = volumes
        if include_trim:
            trim, collection_status["trim"] = _collect(
                "trim", lambda: asdict(check_trim_status(drive))
            )
            storage["trim"] = trim
        if include_mft:
            mft, collection_status["mft"] = _collect(
                "mft", lambda: analyze_mft_health(get_mft_info(drive))
            )
            storage["mft"] = mft
    else:
        storage = {"available": False, "error": "Skipped by operator"}
        collection_status["storage"] = _status(storage, "Skipped by operator")

    filesystem: dict[str, Any] | None = None
    if filesystem_root is not None:
        scan = run_full_scan(
            filesystem_root,
            mode="observe",
            exclude_paths=exclude_paths,
            show_progress=show_progress,
        )
        inventory_scan = scan["inventory"]
        filesystem = {
            "available": True,
            "root": str(filesystem_root),
            "total_files": inventory_scan.total_files,
            "tiny_files": inventory_scan.tiny_files,
            "directories_scanned": inventory_scan.directories_scanned,
            "total_bytes": inventory_scan.total_bytes,
            "finding_count": len(scan["findings"]),
            "findings": scan["findings"],
            "health_score": {
                "overall_score": scan["health_score"].overall_score,
                "severity_band": scan["health_score"].severity_band,
            },
        }
        collection_status["filesystem"] = {"available": True, "error": None}

    findings = list(event_analysis.get("findings", []))
    if include_storage:
        _add_drive_findings(storage.get("drives"), findings)
        _add_section_finding(
            storage.get("disk_space"),
            domain="capacity",
            severity_key="severity",
            title=f"Low free space on {drive}",
            recommendation="Restore safe free-space headroom using reviewed, non-destructive cleanup or data migration.",
            findings=findings,
        )
        _add_section_finding(
            storage.get("mft"),
            domain="filesystem_metadata",
            severity_key="overall_severity",
            title=f"NTFS metadata pressure on {drive}",
            recommendation="Review filesystem-pressure evidence; do not use MFT state to dismiss physical storage faults.",
            findings=findings,
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "comprehensive_system_health",
        "timestamp_utc": timestamp,
        "host": host,
        "mode": "observe",
        "event_lookback_days": lookback_days,
        "assessment": _build_assessment(findings, collection_status),
        "capability": capability,
        "system_inventory": inventory,
        "storage": storage,
        "event_log": event_log,
        "event_analysis": event_analysis,
        "filesystem": filesystem,
        "findings": findings,
        "collection_status": collection_status,
    }
    report["recommendations"] = _recommendations(findings, collection_status)
    return report


def _safe_host(hostname: str) -> str:
    return "".join(character if character.isalnum() or character in "-_." else "_" for character in hostname)


def _default_paths(report: dict[str, Any], output_dir: Path | None) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[4]
    directory = output_dir or repo_root / "data" / "profiles" / _safe_host(report["host"])
    stamp = report["timestamp_utc"].replace("-", "").replace(":", "").split(".")[0] + "Z"
    stem = f"system-health-{stamp}"
    return directory / f"{stem}.json", directory / f"{stem}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate passive whole-machine health evidence as JSON and Markdown.",
    )
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--drive", default="C:")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--no-events", action="store_true")
    parser.add_argument("--no-inventory", action="store_true")
    parser.add_argument("--no-storage", action="store_true")
    parser.add_argument("--no-volumes", action="store_true")
    parser.add_argument("--no-trim", action="store_true")
    parser.add_argument("--no-mft", action="store_true")
    parser.add_argument("--filesystem-root", type=Path)
    parser.add_argument("--exclude", action="append", dest="exclude_paths")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Return exit code 2 after writing reports when critical evidence exists",
    )
    args = parser.parse_args(argv)

    if args.lookback_days < 1:
        parser.error("--lookback-days must be at least 1")
    if args.filesystem_root is not None and not args.filesystem_root.is_dir():
        parser.error("--filesystem-root must be an existing directory")

    report = build_system_health_report(
        lookback_days=args.lookback_days,
        drive=args.drive,
        include_events=not args.no_events,
        include_inventory=not args.no_inventory,
        include_storage=not args.no_storage,
        include_volumes=not args.no_volumes,
        include_trim=not args.no_trim,
        include_mft=not args.no_mft,
        filesystem_root=args.filesystem_root,
        exclude_paths=args.exclude_paths,
        show_progress=args.progress,
    )
    default_json, default_md = _default_paths(report, args.output_dir)
    json_path = args.output_json or default_json
    md_path = args.output_md or default_md
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(build_system_health_markdown(report), encoding="utf-8")

    assessment = report["assessment"]
    print("=" * 72)
    print("VIPER HEALTH COMPREHENSIVE SYSTEM REPORT")
    print("=" * 72)
    print(f"Host:       {report['host']}")
    print(f"Severity:   {assessment['severity'].upper()}")
    print(f"Confidence: {assessment['confidence'].upper()}")
    print(f"Capability: {report['capability']['tier'].upper()} (advisory)")
    print(f"Findings:   {len(report['findings'])}")
    print(f"JSON:       {json_path}")
    print(f"Markdown:   {md_path}")
    print("No benchmarks or mutating operations were run.")

    if args.fail_on_critical and assessment["severity"] == "critical":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
