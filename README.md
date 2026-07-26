# 💚 viper-health

![Status](https://img.shields.io/badge/Status-Active%20Scaffold-success)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PowerShell](https://img.shields.io/badge/PowerShell-7%2B-5391FE?logo=powershell)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-black?logo=githubactions)

## Detect faults • Protect data • Understand the whole machine

Windows system-health diagnostics toolkit focused on hardware/event evidence,
storage reliability, crashes, machine specifications, filesystem pressure, and
safe maintenance boundaries.

[📘 Spec](viper-ssd-health.md) • [🩺 System Reports](docs/SYSTEM-HEALTH-REPORTS.md) • [🚨 P3-512 Incident & Replacement Plan](docs/P3-512-INCIDENT-AND-REPLACEMENT.md) • [🧱 Project Structure](#-project-structure) • [🚀 Quick Start](#-quick-start) • [🛡️ Safety Model](#️-safety-model) • [🧪 CI](#-ci)

---

## 🎯 What is viper-health?

`viper-health` is a Python-led, PowerShell-assisted diagnostics project for
evidence-based Windows system and storage health assessment.

It is designed to:

- detect tiny-file hotspots and directory density anomalies
- detect metadata pressure and churn acceleration over time
- detect cache explosions, cloud-sync churn, and update leftovers
- collect hardware, firmware, OS, drive, event-log, crash, WHEA, memory, and
  display-recovery evidence
- preserve critical paths through strict maintenance guardrails
- produce actionable reports (JSON, Markdown, console)

---

## 📊 Project Status

| Component | Status | Progress | Location |
| --- | --- | --- | --- |
| **Specification** | ✅ Complete (drafted) | v0.3 | [`viper-ssd-health.md`](viper-ssd-health.md) |
| **Python Package Scaffold** | ✅ Complete | baseline | [`python/`](python/) |
| **PowerShell Module Scaffold** | ✅ Complete | baseline | [`powershell/PSViperHealth/`](powershell/PSViperHealth/) |
| **Config Baseline** | ✅ Complete | baseline | [`config/`](config/) |
| **Data Baseline Folders** | ✅ Complete | baseline | [`data/`](data/) |
| **CI Workflow** | ✅ Complete | initial | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| **Core Detectors** | ✅ Complete | tiny-file + density | `python/src/viper_health/` |
| **Health Scoring** | ✅ Complete | weighted scoring | `python/src/viper_health/scoring/` |
| **Reporters** | ✅ Complete | JSON + Markdown | `python/src/viper_health/reports/` |
| **Comprehensive System Report** | ✅ Complete | specs + events + storage + JSON/Markdown | `python/src/viper_health/cli/system_report.py` |
| **Machine Capability Assessment** | ✅ Complete | advisory CPU/GPU/RAM/OS tier + optimizations | `python/src/viper_health/analyzers/spec_assessment.py` |
| **Profiles Index** | ✅ Complete | cross-machine comparison table + latest.* pointers | `python/src/viper_health/cli/profiles_index.py` |
| **Benchmark Preflight** | ✅ Complete | mandatory fail-closed evidence gate | `python/src/viper_health/analyzers/benchmark_preflight.py` |
| **Suite Runner** | ✅ Complete | preset-based scans | `python/src/viper_health/cli/suite.py` |
| **I/O Benchmarks** | ✅ Complete | seq/random read/write | `python/src/viper_health/benchmarks/` |
| **MFT Analysis** | ✅ Complete | size + fragmentation | `python/src/viper_health/collectors/mft_info.py` |
| **TRIM Status** | ✅ Complete | SSD TRIM verification | `python/src/viper_health/collectors/trim_status.py` |
| **Free Space Monitor** | ✅ Complete | SSD headroom thresholds | `python/src/viper_health/collectors/disk_space.py` |
| **Baseline Comparison** | ✅ Complete | trend analysis | `python/src/viper_health/analyzers/baseline_comparison.py` |
| **Metadata Pressure** | ✅ Complete | composite signal (4.3) | `python/src/viper_health/analyzers/metadata_pressure.py` |
| **Churn/Cache Detectors** | ✅ Complete | cloud/browser/update/telemetry (4.4-4.7) | `python/src/viper_health/analyzers/category_pressure.py` |
| **Snapshot & Churn Velocity** | ✅ Complete | files/day trends (Sec 11) | `python/src/viper_health/analyzers/churn.py` |
| **Drive Health / SMART** | ✅ Complete | health/temp/wear | `python/src/viper_health/collectors/smart_data.py` |
| **Process I/O Monitor** | ✅ Complete | top disk-I/O procs | `python/src/viper_health/collectors/io_processes.py` |
| **Maintenance Mode** | ⏸️ Deferred | intentionally observe-only | see [Safety Model](#️-safety-model) |

---

## 🧱 Project Structure

```text
viper-health/
├── docs/                          # Architecture notes + runbooks
├── python/                        # Python package + tests
│   ├── pyproject.toml
│   ├── src/viper_health/
│   │   ├── collectors/
│   │   ├── analyzers/
│   │   ├── scoring/
│   │   ├── reports/
│   │   ├── cli/
│   │   └── utils/
│   └── tests/
├── powershell/PSViperHealth/      # PowerShell module
│   ├── Collectors/
│   ├── Analyzers/
│   ├── Scoring/
│   └── Reports/
├── config/                        # thresholds + path policies
├── data/                          # baselines/snapshots/reports
├── scripts/                       # convenience wrappers
├── viper-ssd-health.md            # authoritative implementation spec
└── README.md
```

### Why this structure?

- ✅ Clear separation of detectors, analyzers, scoring, and reporting
- ✅ Friendly for phased implementation and testing
- ✅ Safe defaults can be centralized in config
- ✅ Automation-ready for CI and future scheduled health runs

---

## 🚀 Quick Start

### Generate a Comprehensive Passive Report

Run from an elevated PowerShell terminal for the best event and reliability
coverage. This does not run a benchmark or filesystem sweep:

```powershell
.venv\Scripts\python.exe -m viper_health.cli.system_report --lookback-days 90
```

Paired JSON and Markdown artifacts are written under
`data/profiles/<HOSTNAME>/`. See
[Comprehensive System Health Reports](docs/SYSTEM-HEALTH-REPORTS.md).

### Running Health Scans

#### Option 1: Use the suite runner (recommended)

List available presets:

```bash
python -m viper_health.cli.suite --list-presets
```

Run a preset scan:

```bash
# Quick check of high-risk areas
python -m viper_health.cli.suite --preset quick-check --console-summary

# Full C: drive sweep with reports (known-stable storage only)
python -m viper_health.cli.suite --preset full-system --output-dir reports/

# User data scan
python -m viper_health.cli.suite --preset user-data --output-dir reports/
```

#### Option 2: Direct scan CLI

```bash
# Scan a specific directory
python -m viper_health.cli.scan C:/Users/scott/AppData/Local --console-summary

# Scan with custom thresholds and output files
python -m viper_health.cli.scan C:/Temp \
  --tiny-warning 15000 \
  --tiny-critical 40000 \
  --output-json report.json \
  --output-md report.md
```

### Available Presets

- `full-system` — Complete C: drive sweep with system exclusions
- `user-data` — All AppData and temp locations
- `quick-check` — High-risk areas (cache, temp, browser data)
- `workspace` — Current directory deep scan
- `cloud-sync` — OneDrive, Dropbox, Google Drive
- `development` — VS Code, nvim, dev tools

See [`config/scan-presets.yaml`](config/scan-presets.yaml) for full preset definitions.

---

### Running I/O Performance Benchmarks

> **Safety warning:** Benchmarks generate sustained reads and writes. Do not run
> them on a disk with recent controller resets, I/O retries, SMART/media errors,
> unexpected storage bugchecks, or an incomplete backup. On the affected
> P3-512 system, `benchmark_io` and `profile_machine --benchmark` are prohibited
> until the disk has been replaced and the replacement path is stable.

Both benchmark entry points enforce a mandatory passive preflight and fail
closed when event coverage or drive reliability data is unavailable, or when
warning/critical evidence exists. There is no override. Results are
measurements for same-machine baseline comparison, not health verdicts.

Benchmarks are optional diagnostics for known-stable storage, not health tests:

```bash
# Quick benchmark on default temp directory
python -m viper_health.cli.benchmark_io

# Benchmark specific drive with larger test file
python -m viper_health.cli.benchmark_io --target D:\ --file-size 200

# Save benchmark results for baseline tracking
python -m viper_health.cli.benchmark_io --output data/benchmarks/baseline.json
```

**What it measures:**

- Sequential write/read throughput and IOPS
- Random write/read throughput and IOPS
- Informational measurements for same-machine baseline comparison

Interpret throughput only against a same-machine, same-configuration baseline.
Generic speed bands are not hardware-health severity thresholds. Windows
storage events and raw SMART errors take precedence over a fast benchmark or
`HealthStatus=Healthy` result.

---

### Analyzing MFT (Master File Table) Health

**Requires administrator privileges** — MFT analysis uses Windows `fsutil` to inspect filesystem metadata:

```bash
# Analyze C: drive MFT (run as Administrator)
python -m viper_health.cli.scan_mft --drive C:

# Save MFT health metrics
python -m viper_health.cli.scan_mft --drive C: --output mft_health.json
```

**What it reports:**

- MFT size in GB and bytes
- MFT fragmentation level
- Total file and folder counts
- Health assessment against spec thresholds (MFT size >2.5 GB, fragments >10)

**To run with elevation:**

1. Open PowerShell or Command Prompt as Administrator
2. Navigate to viper-health directory
3. Run: `.venv\Scripts\python.exe -m viper_health.cli.scan_mft`

---

### Checking TRIM Status

**Requires administrator privileges** — TRIM is critical for SSD health:

```bash
# Check if TRIM is enabled (requires admin)
python -m viper_health.cli.check_trim
```

**What it reports:**

- TRIM enabled/disabled status
- Critical if disabled (drive will continuously degrade without TRIM)
- Fix commands if disabled: `fsutil behavior set DisableDeleteNotify 0`

**CRITICAL:** If TRIM is disabled, file deletions won't improve drive performance!

---

### Monitoring Free Space

Track disk space with SSD-specific thresholds:

```bash
# Check free space on C: drive
python -m viper_health.cli.check_space --drive C:

# Save results
python -m viper_health.cli.check_space --output space_check.json
```

**Thresholds:**

- <10% free = CRITICAL (immediate action needed)
- 10-20% free = WARNING (clean up soon)
- >20% free = GOOD (healthy)

**Why it matters:** SSDs need free-space headroom for wear leveling, garbage
collection, and dynamic cache capacity. More free space is beneficial, but it
does not rule out media, cable, controller, firmware, or power faults.

---

### Comparing to Baseline (Trend Analysis)

Track profile and performance changes over time on known-stable storage. Omit
benchmark sections when storage health is uncertain:

```bash
# Save baseline after cleanup
python -m viper_health.cli.benchmark_io --output data/baselines/baseline.json

# Later, compare current results
python -m viper_health.cli.benchmark_io --output data/benchmarks/current.json
python -m viper_health.cli.compare_baseline --baseline data/baselines/baseline.json --current data/benchmarks/current.json
```

**What it detects:**

- Benchmark throughput degradation (>10% = WARNING, >20% = CRITICAL)
- MFT size growth
- Health score changes
- Improvements after cleanup

**Recommended:** Compare read-only profile metrics regularly. Run benchmarks
only after backup and storage-event preflight checks show no instability.

---

### Scanning Churn / Cache / Residue (spec 4.4-4.7)

Scan the well-known Windows churn hotspots — cloud-sync, browser/WebView
caches, update residue, and telemetry/log directories:

```bash
# Scan all churn categories
python -m viper_health.cli.scan_targets --category all

# Just browser/WebView caches
python -m viper_health.cli.scan_targets --category browser

# Save results
python -m viper_health.cli.scan_targets --category all --output data/reports/targets.json
```

Categories: `cloud`, `browser`, `update`, `telemetry`, `all`.

---

### Tracking Churn Over Time (Snapshots, spec Section 11)

Capture point-in-time snapshots and diff them to compute churn velocity
(files/day) and acceleration:

```bash
# Capture a baseline snapshot of all target roots
python -m viper_health.cli.scan_snapshot capture --output data/snapshots/day1.json

# Later, capture again and diff
python -m viper_health.cli.scan_snapshot capture --output data/snapshots/day2.json
python -m viper_health.cli.scan_snapshot diff --previous data/snapshots/day1.json --current data/snapshots/day2.json
```

---

### Composite Metadata Pressure (spec 4.3)

Combine tiny-file totals, directory counts, and optional MFT signals into a
single pressure score:

```bash
# Analyze a directory tree
python -m viper_health.cli.scan_metadata --root C:\Users\me\AppData

# Include MFT signals (requires admin)
python -m viper_health.cli.scan_metadata --root C:\ --drive C:
```

---

### Drive Health / SMART / Temperature

Query physical disk health, temperature, and wear via Windows Storage cmdlets:

```bash
python -m viper_health.cli.check_smart --output data/reports/smart.json
```

Reports health status, temperature (°C), wear %, power-on hours, and error
counts per physical disk. For detailed vendor SMART attributes, use
CrystalDiskInfo or `smartctl`.

> `HealthStatus=Healthy` and `PredictFailure=False` are threshold summaries, not
> guarantees. Any nonzero read/media/reallocation counters, repeated Event 129
> or 153 records, or storage-related bugchecks require investigation even when
> the summary remains green.

---

### Top Disk-I/O Processes

Identify which processes are generating the most disk I/O (helps diagnose
sustained latency from search indexing, antivirus, or cloud sync):

```bash
python -m viper_health.cli.check_io --top 10
```

---

### Python Development Setup

1. Create/activate Python 3.12+
2. Install in editable mode
3. Run tests

```bash
pip install -e python
pip install -e python[dev]
pytest -v python/tests
```

### PowerShell contributors

```powershell
Import-Module .\powershell\PSViperHealth\PSViperHealth.psd1 -Force
```

### Read the spec first

Before implementing detectors/maintenance logic, read:

- [`viper-ssd-health.md`](viper-ssd-health.md)

---

## 🛡️ Safety Model

This project is intentionally conservative for mutating operations.

Core principles:

- observe/read-only is default
- maintenance mode requires explicit operator intent
- immutable/sensitive roots are protected
- quarantine-first behavior over hard-delete
- dry-run + manifests + action caps are required

Notable protected path example:

- VS Code built-in extension tree under `%LOCALAPPDATA%\Programs\Microsoft VS Code\resources\app\extensions`

---

## 🧪 CI

GitHub Actions runs Python tests on push and pull request to `main`.

- workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## 🤝 Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for workflow, expectations, and safety constraints.

---

## 📜 License

MIT — see [`LICENSE`](LICENSE).

Built with care for long-term system health.
