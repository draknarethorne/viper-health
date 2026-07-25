# Viper SSD Health Specification (Draft v0.2)

This document defines the implementation contract for SSD/filesystem health tooling in the `viper-health` workspace.

> Status: **Draft, intentionally incomplete in a few decision areas** (see Section 14).

---

## 0) System Health & Filesystem Diagnostics — Background Summary

Over time, the system exhibited stalls, slowdowns, and inconsistent latency
(especially during boot and filesystem-heavy workflows). The original working
hypothesis attributed these symptoms to metadata pressure on a DRAM-less QLC
SSD. That hardware identification and root-cause conclusion were incorrect.

The installed system disk identifies only as `P3-512`, firmware `SN18398`, and
Windows reports it as a **512 GB SATA SSD** on the AMD 400-Series chipset SATA
controller. The model string does not establish vendor, NAND type, or DRAM
configuration. Historical Windows events later showed that the primary failure
signal was a long-running Disk 0/SATA-path fault: `storahci` Event 129 resets,
Disk Event 153 retries, storage-oriented bugchecks, read errors, and reported
reallocated blocks. The first retained reset predates this toolkit's benchmark
work by nearly three months.

Tiny-file proliferation, stale caches, cloud-sync churn, update artifacts, and
installer residue can still create metadata pressure and random-I/O cost. They
must not be presented as explanations for controller resets, media errors, or
storage bugchecks without supporting evidence.

Cleanup outcomes (post-remediation state):

- MFT fragmentation: zero
- MFT size: healthy
- tiny-file density: normal
- directory hotspots: primarily expected Windows-heavy zones
- filesystem-pressure metrics: stable baseline

These outcomes describe filesystem state only. They do not certify physical
disk, cable, controller, firmware, or power health.

Incident learned from cleanup:

- VS Code may install under `%LOCALAPPDATA%\Programs`
- During cleanup, `resources/app/extensions` was removed from the VS Code install tree
- That directory contains built-in extensions and core runtime dependencies
- Result: authentication provider and core modules failed to load
- Resolution: full VS Code reinstall restored integrity

Why this spec exists:

- Build diagnostic and maintenance tooling that preserves SSD health long-term
- Detect hotspots/churn/pressure early
- Enforce strict protection boundaries so cleanup cannot damage critical application paths
- Produce reproducible reports and health scoring for decision support

---

## 1) Scope and Goals

Build Python and PowerShell tooling that can:

- detect filesystem churn and small-file pressure
- identify risky growth trends before they become SSD performance issues
- produce reproducible machine-readable and human-readable reports
- remain **safe by default** (read-only unless explicitly run in maintenance mode)

Primary outcomes:

1. Baseline current system storage behavior
2. Detect anomalies/trends over time
3. Score health consistently (0–100)
4. Surface targeted remediation recommendations

---

## 2) Repository Layout (adapted to `viper-health`)

All generated files should live under the `viper-health` root, separated by subdirectories.

```text
viper-health/
├── docs/
│   ├── viper-ssd-health.md                 # this spec
│   ├── architecture/
│   └── runbooks/
│
├── python/
│   ├── pyproject.toml
│   ├── src/viper_health/
│   │   ├── collectors/
│   │   ├── analyzers/
│   │   ├── scoring/
│   │   ├── reports/
│   │   ├── cli/
│   │   └── utils/
│   └── tests/
│
├── powershell/
│   └── PSViperHealth/
│       ├── PSViperHealth.psd1
│       ├── PSViperHealth.psm1
│       ├── Collectors/
│       ├── Analyzers/
│       ├── Scoring/
│       └── Reports/
│
├── config/
│   ├── thresholds.default.yaml
│   ├── allowlist.paths.yaml
│   └── profiles/
│
├── data/
│   ├── baselines/
│   ├── snapshots/
│   └── reports/
│
└── scripts/
    ├── invoke_scan.ps1
    └── invoke_scan.py
```

---

## 3) Execution Modes

All tools must support two modes:

- **Observe mode (default):** read-only, no cleanup/deletion
- **Maintenance mode:** cleanup actions allowed only with explicit switches and audit logging

PowerShell examples of intent:

- `-Mode Observe`
- `-Mode Maintenance -WhatIf`
- `-Mode Maintenance -Confirm:$true`

Python CLI examples of intent:

- `scan --mode observe`
- `scan --mode maintenance --dry-run`

### 3.1 Safety invariants (mandatory)

The following invariants are non-negotiable:

1. No script performs delete/move actions in default execution.
2. Maintenance mode must require explicit operator intent flags.
3. Any mutating action must support a dry-run preview that lists exact candidate paths.
4. Any mutating action must emit an action manifest before execution.
5. Direct hard-delete is disallowed by default; quarantine-first policy applies.
6. Write benchmarks must be opt-in and must refuse to run when preflight finds
   recent storage resets/retries, storage bugchecks, or media/reallocation
   errors unless a future explicit override is deliberately implemented.
7. A green SMART summary, free-space result, MFT result, or filesystem score
   must never overrule concrete storage-event or raw-error evidence.

---

## 3.2 Mutation Gating Model (anti-accidental-delete)

A mutating operation is allowed only if **all** checks pass:

1. Mode is maintenance
2. Dry run has been executed in the current session
3. Candidate paths are within approved cleanup roots
4. Candidate paths are not in immutable/sensitive roots
5. Operator confirmation token is supplied
6. Action caps are not exceeded

If any check fails, operation must abort with no filesystem changes.

---

## 3.3 Immutable and sensitive roots (never auto-clean)

The following are protected by default and excluded from automated cleanup actions:

- `%WINDIR%\System32`
- `%WINDIR%\SysWOW64`
- `%WINDIR%\WinSxS`
- `%WINDIR%\servicing`
- `%WINDIR%\Installer`
- `%ProgramFiles%`
- `%ProgramFiles(x86)%`
- `%ProgramData%` (except explicitly approved transient subpaths)
- `%LOCALAPPDATA%\Programs\Microsoft VS Code\resources\app`
- `%LOCALAPPDATA%\Programs\Microsoft VS Code\resources\app\extensions`
- user profile document/source roots (Desktop, Documents, source repos)

Notes:

- These may still be scanned and reported.
- Cleanup in these roots is denied unless an explicit emergency override profile is used.

---

## 3.4 Approved cleanup roots (allowlist for mutation)

Mutation candidates must fall under explicit approved roots, for example:

- `%LOCALAPPDATA%\Temp`
- browser cache directories
- WebView2 temporary cache directories
- known package-manager temp/cache roots
- `SoftwareDistribution\Download` (with extra safeguards)

Approved roots are centrally managed in `config/allowlist.paths.yaml` and must be canonicalized before matching.

---

## 4) Detector Families

### 4.1 Tiny-file hotspots

- Definition: high counts of files `< 4 KiB`
- Warning: `> 20,000`
- Critical: `> 50,000`

### 4.2 Directory density

- Definition: very high file counts in a single directory tree
- Warning: `> 50,000`
- Critical: `> 100,000`

### 4.3 Metadata pressure

Composite signal from:

- tiny-file totals
- directory counts
- MFT size
- MFT fragmentation
- growth velocity (snapshot-over-snapshot)

Default thresholds:

- MFT size `> 2.5 GiB`
- MFT fragments `> 10`
- tiny files `> 500,000`
- directories `> 200,000`

### 4.4 Cloud-sync churn

Targets:

- OneDrive
- Google Drive
- Dropbox
- VS Code `workspaceStorage`

Indicators:

- created/day `> 10,000`
- deleted/day `> 5,000`
- tiny files in sync roots `> 50,000`

### 4.5 Browser/WebView2 cache churn

Targets:

- Edge WebView2 cache
- Chrome cache
- Discord code cache
- Teams hashed assets

Indicators:

- file count in cache roots `> 50,000`
- created/day `> 10,000`

### 4.6 Update and installer residue

Targets:

- `SoftwareDistribution\Download`
- installer cache roots
- known temporary package staging areas

Indicators:

- update leftovers `> 5 GiB`
- `SoftwareDistribution` file count `> 10,000`

### 4.7 Telemetry/log churn

Targets:

- Diagnostics
- WER
- CBS logs
- `%LOCALAPPDATA%\Temp`

Indicators:

- log files `> 10,000`
- cumulative size `> 5 GiB`

---

## 5) Allowlist / Safe-zone Policy

Detectors must support an allowlist to reduce false positives.

Default safe zones (non-anomalous unless explicit override):

- `WinSxS\Manifests`
- `WinSxS\FileMaps`
- `WinSxS\Backup`
- `Windows\servicing\Packages`
- `System32\CatRoot`
- selected SDK/cache paths declared in `config/allowlist.paths.yaml`

Rules:

1. Allowlisted paths are still measured, but not auto-flagged critical by default
2. Reports must show suppressed findings under a dedicated section
3. Any maintenance action in system folders requires explicit `force` semantics

---

## 6) Health Score Contract (0–100)

Initial weighted model:

- tiny-file pressure: 20
- directory density: 10
- metadata pressure: 20
- MFT health: 15
- storage latency trend: 10
- indexer health/churn: 10
- cache/cloud churn: 15

Scoring:

- each component yields `0..100`
- final score is weighted mean
- severity bands:
  - `85–100`: Good
  - `70–84`: Watch
  - `50–69`: Degraded
  - `<50`: Critical

---

## 7) Output and Report Requirements

### Required formats

- JSON (machine-readable, canonical)
- Markdown (human report)
- Console summary

### JSON schema requirements

Minimum top-level fields:

- `timestamp_utc`
- `host`
- `mode`
- `scan_scope`
- `metrics`
- `findings`
- `suppressed_findings`
- `score`
- `recommendations`

Hardware-health reports must distinguish:

- filesystem pressure and capacity
- drive firmware summary status
- raw reliability/error counters
- operating-system storage/controller events
- unavailable or unsupported evidence

A report must not emit a global “healthy drive” conclusion when only a subset
of those evidence classes was collected.

---

## 8) Logging and Audit Requirements

Every run must log:

- start/end timestamps
- elapsed duration
- files scanned
- directories scanned
- skipped paths and reason
- findings by severity
- threshold sources (default vs profile override)

Maintenance mode must additionally log:

- action intent
- `what-if` result
- confirmed execution events
- post-action verification summary

Maintenance mode must also persist:

- pre-action candidate manifest (full canonical paths + size + reason)
- post-action outcome manifest (success/failed/skipped)
- quarantine location and retention expiry
- rollback metadata (where applicable)

---

## 8.1 Quarantine, rollback, and limits

To avoid destructive mistakes:

1. **Quarantine-first**: default action is move to quarantine, not delete.
2. **Retention window**: quarantined files are retained for a configured period before purge.
3. **Per-run caps**: enforce max files moved and max bytes moved per run.
4. **Per-path caps**: cap actions per top-level root to avoid runaway behavior.
5. **Kill switch**: immediate stop when abnormal error rate or path mismatch is detected.

---

## 8.2 Symlink, junction, and reparse-point safety

Mutating operations must:

- detect symlinks/junctions/reparse points
- avoid traversing or mutating through reparse boundaries by default
- require explicit opt-in to follow links
- log any skipped linked targets with reason

---

## 8.3 Process-awareness safety

Before mutation in cache/temp targets:

- detect active lock/use by critical processes when possible
- skip in-use files and record as deferred
- never force-stop application processes as part of automated cleanup

---

## 8.4 Test requirements for safety controls

Safety behavior must be covered by tests:

- deny mutation outside approved roots
- deny mutation in immutable roots
- verify dry-run-only behavior in observe mode
- verify manifest generation before mutation
- verify cap enforcement and kill-switch activation

---

## 9) Python Implementation Contract

Python modules under `python/src/viper_health/`:

- `collectors/`: gather raw metrics and snapshots
- `analyzers/`: detector logic and classification
- `scoring/`: score model + bands
- `reports/`: JSON/MD/console renderers
- `cli/`: command entrypoints (`scan`, `diff`, `report`)
- `utils/`: path, logging, windows API adapters

Testing requirements:

- unit tests for each detector
- snapshot-diff tests for churn detection
- contract tests for report schema stability

---

## 10) PowerShell Implementation Contract

PowerShell module under `powershell/PSViperHealth/`:

- `Collectors/Get-*.ps1`
- `Analyzers/Test-*.ps1`
- `Scoring/Get-HealthScore.ps1`
- `Reports/Write-*.ps1`

Guidelines:

- return `PSCustomObject` from collectors/analyzers
- avoid formatted strings in core functions (format at output layer only)
- support `-WhatIf` and `-Confirm` for mutating actions

---

## 11) Baselines and Trend Analysis

Store snapshots in `data/snapshots/` and computed baselines in `data/baselines/`.

Trend logic expectations:

- compare current scan to prior snapshot
- compute velocity (files/day, size/day)
- detect acceleration (not only absolute threshold crossing)
- emit “new risk” vs “existing risk” labels

---

## 12) Copilot Generation Rules

When generating code from this spec:

1. Use the directory layout in Section 2
2. Default to observe/read-only behavior
3. Load thresholds from config before applying defaults
4. Emit structured JSON first, then derive Markdown/console
5. Keep detector logic pure/testable
6. Do not hard-delete files outside explicit maintenance flow

---

## 13) Implementation Phases (recommended)

Phase 1:

- inventory collector
- tiny-file + directory-density detectors
- JSON/MD reports

Phase 2:

- metadata/MFT detectors
- cloud-sync + browser churn detectors
- baseline snapshot diffing

Phase 3:

- scoring model calibration
- maintenance workflows with safe guards
- scheduling/runbook docs

---

## 14) Open Decisions (must be finalized before full implementation)

> **Resolution status (2026-07-24):** Most decisions are now settled by the
> Python implementation. Remaining open items are noted inline.

1. **Supported Python version** — ✅ Resolved: `3.12+` (`python/pyproject.toml`).
2. **Preferred config format** — ✅ Resolved: `YAML` (`config/*.yaml`).
3. **Canonical path normalization strategy** — ✅ Resolved: `Path.resolve()` /
   env-var expansion; long/short path edge cases deferred.
4. **Score calibration source** — ✅ Resolved: fixed weights (Section 6).
5. **Maximum scan scope defaults** — ✅ Resolved: targeted roots via presets
   (`config/scan-presets.yaml`); full-system available on demand.
6. **Retention policy** for snapshots/reports — ⏳ Open: outputs are git-ignored;
   no automatic purge yet.
7. **Maintenance action boundary** — ✅ Resolved: **no auto-clean**. Tooling is
   observe-only (see status note below).
8. **Quarantine retention default** — ⏳ Deferred with maintenance mode.
9. **Per-run action caps** — ⏳ Deferred with maintenance mode.
10. **Emergency override process** — ⏳ Deferred with maintenance mode.

---

## 14.1) Implementation Status (2026-07-24)

**Detector families (Section 4): implemented (read-only).**

- 4.1 Tiny-file hotspots — ✅ `analyzers/tiny_file_hotspots.py`
- 4.2 Directory density — ✅ `analyzers/directory_density.py`
- 4.3 Metadata pressure composite — ✅ `analyzers/metadata_pressure.py`
- 4.4 Cloud-sync churn — ✅ `analyzers/category_pressure.py` + `collectors/target_roots.py`
- 4.5 Browser/WebView2 cache churn — ✅ `analyzers/category_pressure.py`
- 4.6 Update/installer residue — ✅ `analyzers/category_pressure.py`
- 4.7 Telemetry/log churn — ✅ `analyzers/category_pressure.py`

**Trend & drive health (Sections 11, plus SSD longevity checks): implemented.**

- Snapshot capture + churn velocity — ✅ `collectors/snapshot.py`, `analyzers/churn.py`
- Baseline comparison — ✅ `analyzers/baseline_comparison.py`
- MFT health — ✅ `collectors/mft_info.py`
- TRIM status — ✅ `collectors/trim_status.py`
- Free space — ✅ `collectors/disk_space.py`
- Drive health / SMART / temperature — ✅ `collectors/smart_data.py`
- Process I/O — ✅ `collectors/io_processes.py`
- I/O measurements — ✅ `benchmarks/io_bench.py`
- Benchmark safety preflight — ✅ `analyzers/benchmark_preflight.py`

`benchmark_io` and `profile_machine --benchmark` fail closed unless Windows
System event coverage and physical-drive reliability counters are available
and contain no warning or critical evidence. There is no override. Absolute
throughput is informational and must be interpreted only against a
same-machine, same-configuration baseline.

**Maintenance mode (Sections 3, 8): intentionally deferred.**

The toolkit is deliberately **observe-only**. It reports cleanup candidates but
never mutates the filesystem. This decision is informed by the VS Code
extension-tree incident (Section 0): automated cleanup is hazardous even with
guardrails. If maintenance mode is added later, it MUST implement the full
mutation-gating model (3.2), immutable-root enforcement (3.3), quarantine-first
policy (8.1), symlink safety (8.2), process-awareness (8.3), and the safety
test suite (8.4) before any mutating action ships.

**PowerShell parity (Section 10): not started.** Python is the reference
implementation; the PowerShell module remains a scaffold.

---

## 15) Immediate Next Step

The directory skeleton (Section 2) exists and Phase 1–2 detectors are
implemented and test-backed. Remaining optional work: detailed vendor SMART
attribute parsing, write-amplification tracking, indexing-service detection,
scheduled runs, and PowerShell parity. Maintenance mode remains deferred by
design.
