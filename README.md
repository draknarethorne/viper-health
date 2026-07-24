# 💚 viper-health

![Status](https://img.shields.io/badge/Status-Active%20Scaffold-success)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![PowerShell](https://img.shields.io/badge/PowerShell-7%2B-5391FE?logo=powershell)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-black?logo=githubactions)

## Detect the churn • Protect the system • Keep the SSD healthy

Filesystem and SSD-health diagnostics toolkit focused on metadata pressure, tiny-file hotspots, churn detection, and safe maintenance boundaries.

[📘 Spec](viper-ssd-health.md) • [🧱 Project Structure](#-project-structure) • [🚀 Quick Start](#-quick-start) • [🛡️ Safety Model](#️-safety-model) • [🧪 CI](#-ci)

---

## 🎯 What is viper-health?

`viper-health` is a dual-stack diagnostics project (Python + PowerShell) built to identify and prevent long-term storage degradation patterns on Windows systems, especially where heavy metadata churn impacts SSD responsiveness.

It is designed to:

- detect tiny-file hotspots and directory density anomalies
- detect metadata pressure and churn acceleration over time
- detect cache explosions, cloud-sync churn, and update leftovers
- preserve critical paths through strict maintenance guardrails
- produce actionable reports (JSON, Markdown, console)

---

## 📊 Project Status

| Component | Status | Progress | Location |
| --- | --- | --- | --- |
| **Specification** | ✅ Complete (drafted) | v0.2 | [`viper-ssd-health.md`](viper-ssd-health.md) |
| **Python Package Scaffold** | ✅ Complete | baseline | [`python/`](python/) |
| **PowerShell Module Scaffold** | ✅ Complete | baseline | [`powershell/PSViperHealth/`](powershell/PSViperHealth/) |
| **Config Baseline** | ✅ Complete | baseline | [`config/`](config/) |
| **Data Baseline Folders** | ✅ Complete | baseline | [`data/`](data/) |
| **CI Workflow** | ✅ Complete | initial | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| **Core Detectors** | ✅ Complete | tiny-file + density | `python/src/viper_health/` |
| **Health Scoring** | ✅ Complete | weighted scoring | `python/src/viper_health/scoring/` |
| **Reporters** | ✅ Complete | JSON + Markdown | `python/src/viper_health/reports/` |
| **Suite Runner** | ✅ Complete | preset-based scans | `python/src/viper_health/cli/suite.py` |

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

# Full C: drive sweep with reports
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
