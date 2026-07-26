"""Generate a cross-machine index for ``data/profiles/``.

Scans each host directory for its newest comprehensive ``system-health-*.json``
report, extracts a one-line summary, and writes:

- ``data/profiles/INDEX.md`` — a comparison table across all machines
- ``data/profiles/<HOST>/latest.json`` and ``latest.md`` — stable pointers to
  each host's newest report so the current state is visible without hunting for
  timestamps.

Read-only apart from writing the index and copying the newest report to the
``latest.*`` names.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_profiles_dir() -> Path:
    # profiles_index.py -> cli -> viper_health -> src -> python -> <repo root>
    return Path(__file__).resolve().parents[4] / "data" / "profiles"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _newest_report(host_dir: Path) -> Path | None:
    reports = sorted(
        (p for p in host_dir.glob("system-health-*.json") if p.stem != "latest"),
        reverse=True,
    )
    return reports[0] if reports else None


def _gib(value: object) -> str:
    try:
        return f"{int(value) / (1024 ** 3):.0f} GiB"
    except (TypeError, ValueError):
        return "?"


def _short_cpu(name: str) -> str:
    return " ".join(str(name).replace("(R)", "").replace("(TM)", "").split())[:32]


def _profile_machine_ratio(profiles_dir: Path, host: str) -> float | None:
    """Find tiny_file_ratio from a matching profile_machine ``<host>.json``."""
    candidate = profiles_dir / f"{host}.json"
    data = _load_json(candidate) if candidate.exists() else None
    if isinstance(data, dict):
        ratio = data.get("tiny_file_ratio")
        if isinstance(ratio, (int, float)):
            return float(ratio)
    return None


def collect_machine_rows(profiles_dir: Path) -> list[dict[str, Any]]:
    """Extract one summary row per host from newest system-health reports."""
    rows: list[dict[str, Any]] = []
    if not profiles_dir.is_dir():
        return rows

    for host_dir in sorted(p for p in profiles_dir.iterdir() if p.is_dir()):
        report_path = _newest_report(host_dir)
        if report_path is None:
            continue
        report = _load_json(report_path)
        if not isinstance(report, dict):
            continue

        inventory = report.get("system_inventory") or {}
        system = inventory.get("ComputerSystem") or {}
        os_info = inventory.get("OperatingSystem") or {}
        cpus = inventory.get("Cpu") or []
        if isinstance(cpus, dict):
            cpus = [cpus]
        cpu_name = _short_cpu(cpus[0].get("Name", "")) if cpus else "?"

        storage = report.get("storage") or {}
        drives = storage.get("drives")
        drive0 = drives[0] if isinstance(drives, list) and drives else {}
        disk_space = storage.get("disk_space") or {}

        assessment = report.get("assessment") or {}
        capability = report.get("capability") or {}

        rows.append(
            {
                "host": report.get("host", host_dir.name),
                "model": f"{str(system.get('Manufacturer') or '').strip()} {str(system.get('Model') or '').strip()}".strip() or "?",
                "cpu": cpu_name,
                "ram": _gib(system.get("TotalPhysicalMemoryBytes")),
                "capability": str(capability.get("tier", "unknown")).upper(),
                "os": str(os_info.get("Caption") or "?"),
                "drive": str(drive0.get("friendly_name") or "?"),
                "bus": str(drive0.get("bus_type") or "?"),
                "wear": drive0.get("wear_percent"),
                "free_percent": disk_space.get("free_percent"),
                "severity": str(assessment.get("severity", "unknown")).upper(),
                "confidence": str(assessment.get("confidence", "unknown")).upper(),
                "tiny_file_ratio": _profile_machine_ratio(profiles_dir, report.get("host", host_dir.name)),
                "timestamp": report.get("timestamp_utc", "?"),
            }
        )
    return rows


def _fmt(value: object, suffix: str = "") -> str:
    if value is None:
        return "?"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def build_index_markdown(rows: list[dict[str, Any]]) -> str:
    """Render the machine comparison table as Markdown."""
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Viper Health — Machine Index",
        "",
        f"_Generated (UTC): {generated}_",
        "",
        "One row per machine from its newest `system-health-*.json`. Fault",
        "severity is evidence-based; capability is advisory (specs only).",
        "",
    ]
    if not rows:
        lines.extend(["No machine reports found under `data/profiles/`.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| Machine | Fault | Conf. | Capability | Model | CPU | RAM | Primary drive | Bus | Wear | Free | Tiny % | Report (UTC) |",
            "| --- | --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {host} | {severity} | {confidence} | {capability} | {model} | {cpu} | {ram} | "
            "{drive} | {bus} | {wear} | {free} | {tiny} | {ts} |".format(
                host=row["host"],
                severity=row["severity"],
                confidence=row["confidence"],
                capability=row["capability"],
                model=row["model"],
                cpu=row["cpu"],
                ram=row["ram"],
                drive=row["drive"],
                bus=row["bus"],
                wear=_fmt(row["wear"], "%"),
                free=_fmt(row["free_percent"], "%"),
                tiny=_fmt(row["tiny_file_ratio"], "%"),
                ts=str(row["timestamp"]).split("T")[0],
            )
        )
    lines.append("")
    lines.extend(
        [
            "## Legend",
            "",
            "- **Fault**: evidence-based health (GOOD/WARNING/CRITICAL) from events + storage.",
            "- **Conf.**: collection confidence (HIGH needs elevation).",
            "- **Capability**: advisory specs tier (SOLID/CAPABLE/DATED/WEAK) — never masks a fault.",
            "- **Wear**: SSD wear indicator; low is good. `?` means not readable (e.g. RAID/VMD).",
            "- **Tiny %**: tiny-file ratio from `profile_machine` (lower is better).",
            "",
        ]
    )
    return "\n".join(lines)


def write_latest_pointers(profiles_dir: Path) -> list[Path]:
    """Copy each host's newest report to ``latest.json`` / ``latest.md``."""
    written: list[Path] = []
    if not profiles_dir.is_dir():
        return written
    for host_dir in sorted(p for p in profiles_dir.iterdir() if p.is_dir()):
        report_path = _newest_report(host_dir)
        if report_path is None:
            continue
        latest_json = host_dir / "latest.json"
        shutil.copyfile(report_path, latest_json)
        written.append(latest_json)
        md_source = report_path.with_suffix(".md")
        if md_source.exists():
            latest_md = host_dir / "latest.md"
            shutil.copyfile(md_source, latest_md)
            written.append(latest_md)
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: build the machine index and latest.* pointers."""
    parser = argparse.ArgumentParser(
        description="Build a cross-machine index for data/profiles/.",
    )
    parser.add_argument("--profiles-dir", type=Path, default=_repo_profiles_dir())
    parser.add_argument("--output", type=Path, help="INDEX.md output path")
    parser.add_argument(
        "--no-latest",
        action="store_true",
        help="Do not write per-host latest.json/latest.md pointers",
    )
    args = parser.parse_args(argv)

    rows = collect_machine_rows(args.profiles_dir)
    markdown = build_index_markdown(rows)
    output = args.output or (args.profiles_dir / "INDEX.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

    latest_written = [] if args.no_latest else write_latest_pointers(args.profiles_dir)

    print(f"Indexed {len(rows)} machine(s) → {output}")
    if latest_written:
        print(f"Updated {len(latest_written)} latest.* pointer(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
