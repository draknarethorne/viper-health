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

from viper_health.analyzers.machine_ranking import (
    rank_machines,
    resource_spec_scores,
    storage_expected_vs_actual,
)


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


def _primary_drive(drives: object) -> dict:
    """Choose the most representative internal drive from a drive list.

    Prefers an internal (non-USB, non-removable) drive so external disks do not
    misrepresent a machine's primary storage in the ranking layers.
    """
    if not isinstance(drives, list) or not drives:
        return {}
    internal = [
        d for d in drives
        if isinstance(d, dict) and "usb" not in str(d.get("bus_type", "")).lower()
    ]
    return (internal or drives)[0] if internal or drives else {}


def _profile_machine_data(profiles_dir: Path, host: str) -> dict[str, Any]:
    """Load a matching profile_machine ``<host>.json`` (tiny-file + benchmarks)."""
    candidate = profiles_dir / f"{host}.json"
    data = _load_json(candidate) if candidate.exists() else None
    if not isinstance(data, dict):
        return {"tiny_file_ratio": None, "benchmarks": {}}
    ratio = data.get("tiny_file_ratio")
    benchmarks: dict[str, float] = {}
    for item in data.get("benchmark_results") or []:
        if isinstance(item, dict) and isinstance(item.get("throughput_mb_s"), (int, float)):
            benchmarks[str(item.get("test_name"))] = float(item["throughput_mb_s"])
    return {
        "tiny_file_ratio": float(ratio) if isinstance(ratio, (int, float)) else None,
        "benchmarks": benchmarks,
    }


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
        drive0 = _primary_drive(drives)
        disk_space = storage.get("disk_space") or {}

        assessment = report.get("assessment") or {}
        capability = report.get("capability") or {}
        host = report.get("host", host_dir.name)
        profile_data = _profile_machine_data(profiles_dir, host)

        rows.append(
            {
                "host": host,
                "model": f"{str(system.get('Manufacturer') or '').strip()} {str(system.get('Model') or '').strip()}".strip() or "?",
                "cpu": cpu_name,
                "ram": _gib(system.get("TotalPhysicalMemoryBytes")),
                "capability": str(capability.get("tier", "unknown")).upper(),
                "capability_components": capability.get("components") or {},
                "recommendations": list(capability.get("recommendations") or []),
                "os": str(os_info.get("Caption") or "?"),
                "drive": str(drive0.get("friendly_name") or "?"),
                "bus": str(drive0.get("bus_type") or "?"),
                "media_type": str(drive0.get("media_type") or ""),
                "wear": drive0.get("wear_percent"),
                "free_percent": disk_space.get("free_percent"),
                "trim_enabled": (storage.get("trim") or {}).get("trim_enabled") if isinstance(storage.get("trim"), dict) else None,
                "mft_severity": (storage.get("mft") or {}).get("overall_severity") if isinstance(storage.get("mft"), dict) else None,
                "severity": str(assessment.get("severity", "unknown")).upper(),
                "confidence": str(assessment.get("confidence", "unknown")).upper(),
                "tiny_file_ratio": profile_data["tiny_file_ratio"],
                "benchmarks": profile_data["benchmarks"],
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


def _score_cell(value: object) -> str:
    return "—" if value is None else f"{float(value):.0f}"


def build_index_markdown(rows: list[dict[str, Any]]) -> str:
    """Render layered machine rankings as Markdown.

    Layers: (1) overall performance & configuration ranking, (2) per-resource
    spec scores, (3) storage spec-vs-actual to expose degradation/underperformance,
    (4) per-machine tuning recommendations, plus a raw detail table.
    """
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Viper Health — Machine Index",
        "",
        f"_Generated (UTC): {generated}_",
        "",
        "Layered rankings across machines. **Fault severity is health**; the",
        "ranking score is an advisory performance & configuration aid and never",
        "overrides a fault (WARNING/CRITICAL machines are capped).",
        "",
    ]
    if not rows:
        lines.extend(["No machine reports found under `data/profiles/`.", ""])
        return "\n".join(lines)

    ranked = rank_machines(rows)

    # --- Layer 1: overall ranking ------------------------------------------
    lines.extend(
        [
            "## Layer 1 — Overall ranking (performance & configuration)",
            "",
            "| Rank | Machine | Score | Fault | Capability | Cap. | Config | Perf | Notes |",
            "| ---: | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in ranked:
        ranking = entry["ranking"]
        components = ranking["components"]
        note = "fault-capped" if ranking["fault_limited"] else ""
        lines.append(
            f"| {entry['rank']} | {entry['host']} | {_score_cell(ranking['score'])} | "
            f"{entry['severity']} | {entry['capability']} | "
            f"{_score_cell(components['capability'])} | {_score_cell(components['configuration'])} | "
            f"{_score_cell(components['performance'])} | {note} |"
        )
    lines.append("")

    # --- Layer 2: per-resource spec scores ---------------------------------
    lines.extend(
        [
            "## Layer 2 — Per-resource spec scores",
            "",
            "Raw specification strength per resource (0-100), independent of measured performance.",
            "",
            "| Machine | CPU | Memory | GPU | Storage class |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for entry in ranked:
        spec = resource_spec_scores(entry)
        lines.append(
            f"| {entry['host']} | {_score_cell(spec['cpu'])} | {_score_cell(spec['memory'])} | "
            f"{_score_cell(spec['gpu'])} | {_score_cell(spec['storage'])} |"
        )
    lines.append("")

    # --- Layer 3: storage spec vs actual -----------------------------------
    lines.extend(
        [
            "## Layer 3 — Storage: spec vs actual",
            "",
            "Measured I/O throughput compared to the drive's class ceiling. Low",
            "efficiency flags degradation or entry-tier hardware (e.g. DRAM-less).",
            "Requires a `profile_machine --benchmark` run; otherwise `not measured`.",
            "",
            "| Machine | Class | Seq write | Seq read | Rand write | Rand read | Efficiency | Verdict |",
            "| --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for entry in ranked:
        sva = storage_expected_vs_actual(entry)
        if not sva["available"]:
            lines.append(
                f"| {entry['host']} | {sva['storage_class'].upper()} | — | — | — | — | — | not measured |"
            )
            continue
        by_test = {test["test"]: test for test in sva["tests"]}

        def _cell(name: str) -> str:
            test = by_test.get(name)
            if test is None:
                return "—"
            return f"{test['actual_mb_s']:.0f}/{test['expected_mb_s']:.0f}"

        lines.append(
            f"| {entry['host']} | {sva['storage_class'].upper()} | {_cell('sequential_write')} | "
            f"{_cell('sequential_read')} | {_cell('random_write')} | {_cell('random_read')} | "
            f"{sva['mean_efficiency']:.0%} | {sva['verdict']} |"
        )
    lines.extend(
        [
            "",
            "_Cells show actual/expected MB/s. Efficiency is the mean of actual÷expected._",
            "",
        ]
    )

    # --- Layer 4: per-machine tuning recommendations -----------------------
    lines.extend(["## Layer 4 — Tuning & optimization recommendations", ""])
    any_recs = False
    for entry in ranked:
        recs = entry.get("recommendations") or []
        if not recs:
            continue
        any_recs = True
        lines.append(f"### {entry['host']}")
        for rec in recs:
            lines.append(f"- {rec}")
        lines.append("")
    if not any_recs:
        lines.extend(["No specification-level recommendations were recorded.", ""])

    # --- Raw detail table ---------------------------------------------------
    lines.extend(
        [
            "## Machine details",
            "",
            "| Machine | Fault | Conf. | Model | CPU | RAM | Primary drive | Bus | Wear | Free | Tiny % | Report (UTC) |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in ranked:
        lines.append(
            "| {host} | {severity} | {confidence} | {model} | {cpu} | {ram} | "
            "{drive} | {bus} | {wear} | {free} | {tiny} | {ts} |".format(
                host=entry["host"],
                severity=entry["severity"],
                confidence=entry["confidence"],
                model=entry["model"],
                cpu=entry["cpu"],
                ram=entry["ram"],
                drive=entry["drive"],
                bus=entry["bus"],
                wear=_fmt(entry["wear"], "%"),
                free=_fmt(entry["free_percent"], "%"),
                tiny=_fmt(entry["tiny_file_ratio"], "%"),
                ts=str(entry["timestamp"]).split("T")[0],
            )
        )
    lines.append("")
    lines.extend(
        [
            "## Legend",
            "",
            "- **Fault**: evidence-based health (GOOD/WARNING/CRITICAL) from events + storage.",
            "- **Score**: advisory performance & configuration rank (0-100); WARNING caps at 60, CRITICAL at 25.",
            "- **Cap./Config/Perf**: score components (capability specs, config hygiene, measured I/O).",
            "- **Capability**: advisory specs tier (SOLID/CAPABLE/DATED/WEAK) — never masks a fault.",
            "- **Layer 3 verdict**: meets / below / well below the drive's class expectation.",
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
