# Session Handoff - Viper Health

> **SUPERSEDED 2026-07-25:** The “live system healthy” and “DRAM-less QLC”
> assumptions below are incorrect. `P3-512` is a SATA SSD of unconfirmed vendor,
> NAND, and DRAM configuration. Retained Windows logs show storage failures
> beginning 2026-04-30. Do not run benchmarks on it. Current guidance:
> [`docs/P3-512-INCIDENT-AND-REPLACEMENT.md`](../docs/P3-512-INCIDENT-AND-REPLACEMENT.md).

**Last Updated:** 2026-07-25
**Status:** Disk 0 / P3-512 storage path is unreliable; backup and replacement are urgent.

> Read `tmp/complete-analysis-07242026-1730.md` for the full analysis + assessment.

## CURRENT STATE (2026-07-24 17:30)

All spec Section 4 detector families + drive-health checks are implemented,
tested (130 passing), and validated on the live system — everything healthy.
Maintenance mode intentionally deferred (observe-only).

### CLI surface (`python -m viper_health.cli.<name>`)

`scan`, `suite`, `scan_tiny_files`, `scan_directory_density`, `scan_metadata`
(4.3), `scan_targets` (4.4-4.7 churn/cache), `scan_snapshot` (Sec 11
capture/diff), `scan_mft` (admin), `check_trim` (admin), `check_space`,
`check_smart`, `check_io`, `benchmark_io`, `compare_baseline`.
Wrappers: `scripts/invoke_scan.py` / `.ps1`.

### New this session (spec Option 2)

Modules: `utils/fs_counter.py`, `collectors/target_roots.py`,
`analyzers/category_pressure.py`, `collectors/snapshot.py`, `analyzers/churn.py`,
`analyzers/metadata_pressure.py`, `collectors/smart_data.py`,
`collectors/io_processes.py`.
CLIs: `scan_targets`, `scan_snapshot`, `scan_metadata`, `check_smart`, `check_io`.
Tests: +50 (total 130). Docs aligned: README, monitoring guide, spec (14 + 14.1),
copilot-instructions, thresholds config.

### Validation

```bash
cd /c/Viper-Health && .venv/Scripts/python.exe -m pytest python/tests/ -q   # 130 passed
export PYTHONIOENCODING=utf-8   # needed in bash so emoji output doesn't crash
```

Gotcha: avoid `$_` in inline `powershell -Command` from git-bash (bash mangles
it) — use a `.ps1` file or Python.

### User's immediate to-do

1. Back up critical data to known-good storage.
2. Do not run `benchmark_io` or `profile_machine --benchmark`.
3. Physically verify whether the OEM board has a populated M-key M.2 2280 slot.
4. Replace the P3-512 using the tracked incident/replacement plan.

### Do NOT

Build maintenance/cleanup mode without full spec safety model (mutation gating,
immutable roots, quarantine-first, kill-switch, safety tests). Prior incident:
auto-cleanup once deleted VS Code built-in extensions.

Do not run write benchmarks, full-drive stress tests, or defragmentation on the
P3-512. Historical details below are retained only as a record of the original,
incorrect working hypothesis.

---

<details>
<summary>Earlier session notes (superseded — kept for history)</summary>

# Session Handoff - Viper Health SSD Monitoring Implementation

**Last Updated:** 2026-07-24
**Session Context:** Complete implementation of missing SSD health analyzers

---

## What Was Built This Session

### Core Problem Solved
User requested comprehensive SSD health monitoring for DRAM-less QLC drive after cleanup. Identified critical missing analyzers and built them all in one iteration.

### Implemented Features (All New)

#### 1. I/O Performance Benchmarking ✅
- **Files:** `python/src/viper_health/benchmarks/io_bench.py`, `cli/benchmark_io.py`
- **Purpose:** Measure sequential/random read/write throughput and IOPS
- **Thresholds:** Calibrated for DRAM-less QLC SSDs
- **CLI:** `python -m viper_health.cli.benchmark_io`
- **Tests:** 12 comprehensive tests

**Key Features:**
- Sequential write <100 MB/s = CRITICAL, 100-200 = WARNING, >200 = GOOD
- Random write <20 MB/s = CRITICAL, 20-50 = WARNING (typical DRAM-less QLC)
- Color-coded output with detailed recommendations
- Explains "calm phase" concept (60-min TRIM + garbage collection recovery)

#### 2. MFT Health Analysis ✅
- **Files:** `python/src/viper_health/collectors/mft_info.py`, `cli/scan_mft.py`
- **Purpose:** Track Master File Table size and fragmentation
- **Thresholds:** >2.5 GB CRITICAL, >10 fragments CRITICAL (from spec)
- **CLI:** `python -m viper_health.cli.scan_mft --drive C:` **(requires admin)**
- **Tests:** 8 comprehensive tests

**Key Features:**
- Uses Windows `fsutil fsinfo ntfsinfo` to query MFT
- Reports file/folder counts and metadata pressure
- Provides defragmentation guidance (`defrag C: /U /V`)

#### 3. TRIM Status Verification ✅
- **Files:** `python/src/viper_health/collectors/trim_status.py`, `cli/check_trim.py`
- **Purpose:** Verify TRIM is enabled (critical for SSD health)
- **CLI:** `python -m viper_health.cli.check_trim` **(requires admin)**
- **Tests:** 5 comprehensive tests

**Key Features:**
- Checks `fsutil behavior query DisableDeleteNotify`
- 0 = TRIM enabled (GOOD), 1 = TRIM disabled (CRITICAL)
- Provides fix commands if disabled

#### 4. Free Space Monitoring ✅
- **Files:** `python/src/viper_health/collectors/disk_space.py`, `cli/check_space.py`
- **Purpose:** Track free space with SSD-specific thresholds
- **Thresholds:** <10% CRITICAL, 10-20% WARNING, >20% GOOD
- **CLI:** `python -m viper_health.cli.check_space --drive C:`
- **Tests:** 7 comprehensive tests

**Key Features:**
- Explains why QLC SSDs need 15-20% free space
- Recommends cleanup targets based on severity
- No admin required

#### 5. Baseline Comparison & Trend Analysis ✅
- **Files:** `python/src/viper_health/analyzers/baseline_comparison.py`, `cli/compare_baseline.py`
- **Purpose:** Compare current metrics to saved baselines, detect degradation
- **CLI:** `python -m viper_health.cli.compare_baseline --baseline baseline.json --current current.json`
- **Tests:** 11 comprehensive tests

**Key Features:**
- Compares benchmark throughput, MFT size, health scores
- Detects >10% degradation (WARNING), >20% (CRITICAL)
- Tracks improvements vs degradation over time
- Generates actionable alerts

---

## Enhanced Guidance System

### All CLIs Now Provide Context-Aware Recommendations

**Benchmark CLI:**
- CRITICAL: Explains SLC cache exhaustion, metadata pressure, thermal throttling
- Provides step-by-step diagnosis (free space → TRIM → MFT → calm phase)
- Links to related health checks

**MFT Scan CLI:**
- CRITICAL: Identifies cleanup targets (browser cache, VS Code, packages)
- Explains defragmentation timing and commands
- Post-cleanup verification workflow

**New CLIs:**
- Each provides severity-specific guidance
- Cross-references related analyzers
- Explains "why" behind thresholds

---

## Documentation Created

### 1. SSD Health Monitoring Guide (Comprehensive)
- **File:** `docs/SSD-HEALTH-MONITORING-GUIDE.md` (20+ pages)
- **Contents:**
  - Complete gap analysis (what's implemented vs missing)
  - Prioritized roadmap for future features
  - Deep troubleshooting workflows
  - QLC SSD behavior explained
  - Daily/weekly/monthly monitoring schedules

### 2. Quick Reference (Concise)
- **File:** `docs/QUICK-REFERENCE.md` (concise)
- **Contents:**
  - Three methods to run with admin privileges in VS Code
  - Essential admin-required commands
  - Post-cleanup workflow
  - "Calm phase" timing and verification
  - Quick win troubleshooting checklist

---

## Test Coverage

**Total Tests:** 80 (57 existing + 23 new)
- I/O Benchmarks: 12 tests
- MFT Analysis: 8 tests
- TRIM Status: 5 tests
- Disk Space: 7 tests
- Baseline Comparison: 11 tests

**All tests passing:** ✅

---

## Key User Insights from This Session

### User's Drive Performance (Measured Today)
- Sequential Write: **149 MB/s** (WARNING - cache under pressure)
- Sequential Read: 1095 MB/s (GOOD)
- Random Write: **40 MB/s** (WARNING - typical DRAM-less QLC)
- Random Read: 504 MB/s (GOOD)

### Critical Findings
1. **Write performance degrading** - moderate sequential write indicates SLC cache stress
2. **Post-cleanup calm phase needed** - user cleaned up files today, needs 60-min idle
3. **MFT scan requires elevation** - user needs to restart VS Code as admin

### User Workflow Established
1. Run cleanup
2. Wait 60 minutes (calm phase - TRIM + garbage collection)
3. Re-run benchmarks to measure improvement
4. Check TRIM status, free space, MFT health
5. Compare to baselines weekly

---

## What's Still Missing (Future Work)

### High Priority
- **Drive Temperature Monitoring:** Needs external tool (CrystalDiskInfo) or WMI integration
- **SMART Data Analysis:** Requires `smartctl` or WMI, detects drive failure early
- **Combined Health Dashboard:** Single CLI that runs all checks and generates comprehensive report

### Medium Priority
- **Background Process I/O Monitor:** Identify what's hammering the disk
- **Indexing Service Detection:** Check if Windows Search is causing issues
- **Defragmentation Scheduler:** Automate MFT defrag after cleanup

### Low Priority
- **Firmware Version Check:** Compare to manufacturer recommendations
- **Over-Provisioning Calculator:** Recommend space reservation
- **Power Loss Protection Check:** Detect if drive has PLP

---

## Running with Admin Privileges (Critical for Some Features)

### Method 1: Restart VS Code as Administrator (Recommended)
1. Close VS Code
2. Right-click VS Code icon → "Run as administrator"
3. Open viper-health workspace
4. All terminals now have admin privileges

### Method 2: Elevated PowerShell from VS Code
```powershell
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "cd '$PWD'"
```

### Admin-Required Commands
- `python -m viper_health.cli.scan_mft --drive C:`
- `python -m viper_health.cli.check_trim`
- `fsutil behavior query DisableDeleteNotify`
- `defrag C: /U /V`

---

## Recommended Next Actions (User's Immediate To-Do)

### 1. Verify TRIM is Enabled
```bash
# Requires admin
python -m viper_health.cli.check_trim
```
**If disabled, drive will continuously degrade!**

### 2. Check Free Space
```bash
python -m viper_health.cli.check_space --drive C:
```
**Target: >20% free for optimal QLC performance**

### 3. Allow Calm Phase (60 minutes)
After today's cleanup, let drive idle while:
- Windows sends TRIM commands
- SSD runs garbage collection
- SLC cache recovers

### 4. Re-Run Benchmark (After Calm Phase)
```bash
python -m viper_health.cli.benchmark_io --output data/benchmarks/post_calm.json
```
Compare to earlier benchmark - sequential write should improve

### 5. Save Baselines
```bash
# After calm phase and verification
python -m viper_health.cli.benchmark_io --output data/baselines/baseline_2026-07-24.json
python -m viper_health.cli.scan_mft --drive C: --output data/mft/baseline_2026-07-24.json
```

### 6. Weekly Monitoring
```bash
# Compare to baseline
python -m viper_health.cli.benchmark_io --output data/benchmarks/weekly.json
python -m viper_health.cli.compare_baseline --baseline data/baselines/baseline_2026-07-24.json --current data/benchmarks/weekly.json
```

---

## Important Concepts Explained

### "Calm Phase" (Critical for QLC SSDs)
**What:** 60-minute idle period after heavy I/O or cleanup
**Why:** Allows TRIM + garbage collection + SLC cache recovery
**How:** No active file operations (light browsing OK, no gaming/editing)
**Verify:** Re-run benchmark - sequential write should improve

### TRIM Status
**What:** OS tells SSD which blocks are free
**Why:** Without TRIM, drive can't reclaim deleted space efficiently
**Check:** `fsutil behavior query DisableDeleteNotify` (0 = enabled)
**Critical:** If disabled (=1), cleanup won't improve performance!

### Free Space Threshold (20%)
**Why QLC needs more:** Wear leveling, garbage collection, SLC cache size
**Impact of <10%:** Severe performance degradation, cache shrinks
**User's drive:** Check current free % and compare to thresholds

---

## File Structure of New Code

```
python/src/viper_health/
├── benchmarks/
│   ├── __init__.py
│   └── io_bench.py              # Sequential/random I/O tests
├── collectors/
│   ├── mft_info.py              # MFT size + fragmentation
│   ├── trim_status.py           # TRIM enabled check
│   └── disk_space.py            # Free space monitor
├── analyzers/
│   └── baseline_comparison.py   # Trend analysis
└── cli/
    ├── benchmark_io.py          # I/O benchmark CLI
    ├── scan_mft.py              # MFT health CLI
    ├── check_trim.py            # TRIM status CLI
    ├── check_space.py           # Free space CLI
    └── compare_baseline.py      # Baseline comparison CLI

python/tests/
├── test_io_benchmark.py         # 12 tests
├── test_mft_info.py             # 8 tests
├── test_trim_status.py          # 5 tests
├── test_disk_space.py           # 7 tests
└── test_baseline_comparison.py  # 11 tests

docs/
├── SSD-HEALTH-MONITORING-GUIDE.md   # Comprehensive guide
└── QUICK-REFERENCE.md               # Quick commands
```

---

## Commits Made This Session

1. **feat: Add SSD I/O benchmarks and MFT health analysis** (`cfe9932`)
   - Initial implementation of benchmarks and MFT
   - 57 tests passing

2. **feat: Add comprehensive guidance to benchmark and MFT CLIs** (`746f1cd`)
   - Enhanced recommendations and troubleshooting

3. **docs: Add comprehensive monitoring guide and quick reference** (`3489e31`)
   - Complete documentation for gap analysis and workflows

4. **(Next commit will include new analyzers and tests)**

---

## Resuming This Session

### Context You'll Need
1. User has DRAM-less QLC SSD showing moderate write degradation
2. User performed cleanup today and needs to wait for calm phase
3. User wants to establish baseline and weekly monitoring workflow
4. All high-priority analyzers now implemented
5. Focus next: Combined health dashboard, temperature/SMART (optional)

### Quick Context Refresh
Read this file, then check:
- `docs/SSD-HEALTH-MONITORING-GUIDE.md` - What's missing and why
- `docs/QUICK-REFERENCE.md` - Essential commands
- Latest commit messages for implementation details

### Suggested Next Steps for New Session
1. Create combined health check CLI (runs all analyzers in one command)
2. Add optional temperature/SMART collectors (graceful degradation if tools missing)
3. Update README.md with new features
4. Create PowerShell equivalents for Windows-native workflows
5. Build automated weekly monitoring script

---

## User's Coding Style / Preferences

- **"Cavalier about getting things done"** - Prefers action over discussion
- Wants complete solutions, not just suggestions
- Values clear, actionable recommendations in CLIs
- Appreciates color-coded, icon-driven output (✅⚠️❌)
- Needs admin privilege workarounds explained clearly
- Wants session continuity without losing context

---

## Git Status at Session End

**Branch:** main
**Commits ahead:** 0 (all pushed to origin)
**Uncommitted changes:** New analyzers + tests (ready to commit)
**Test status:** 80/80 passing

---

## Command Quick Reference for New Session

### Run Full Test Suite
```bash
cd /c/Viper-Health
.venv/Scripts/python.exe -m pytest python/tests/ -v
```

### Test New Features Specifically
```bash
pytest python/tests/test_trim_status.py python/tests/test_disk_space.py python/tests/test_baseline_comparison.py -v
```

### Try New CLIs (Non-Admin)
```bash
python -m viper_health.cli.check_space --drive C:
python -m viper_health.cli.benchmark_io
```

### Try New CLIs (Admin Required)
```bash
# Restart VS Code as admin first!
python -m viper_health.cli.check_trim
python -m viper_health.cli.scan_mft --drive C:
```

### Compare to Baseline
```bash
python -m viper_health.cli.compare_baseline --baseline data/baselines/baseline.json --current data/benchmarks/current.json
```

---

## Session Completion Checklist

- [x] Build TRIM status checker
- [x] Build free space monitor
- [x] Build baseline comparison analyzer
- [x] Add comprehensive CLIs for all features
- [x] Add 23 tests (all passing)
- [x] Create comprehensive documentation
- [x] Update .gitignore for tmp/
- [x] Create session handoff document
- [ ] Commit new analyzers and tests
- [ ] Update README.md with new features
- [ ] Push to GitHub

**Next:** Commit and push, then optional: combined health dashboard, temperature/SMART collectors
