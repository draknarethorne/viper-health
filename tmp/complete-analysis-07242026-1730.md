# Viper Health — Complete Analysis (07/24/2026, 17:30)

> **SUPERSEDED — DO NOT USE AS A CURRENT HEALTH ASSESSMENT.** On 2026-07-25,
> full Windows event-history and raw SMART review disproved this report's drive
> identification and “healthy” conclusion. The installed `P3-512` is a 512 GB
> **SATA** SSD, not a confirmed Crucial P3 NVMe/QLC drive. Its vendor, NAND type,
> and DRAM configuration remain unknown. Retained evidence includes 75
> `storahci` resets, 21 Disk 0 retries, storage bugchecks, 13 read errors, and a
> raw SMART attribute 5 value of 13. The first retained failure was 2026-04-30.
> Follow [`docs/P3-512-INCIDENT-AND-REPLACEMENT.md`](../docs/P3-512-INCIDENT-AND-REPLACEMENT.md).
> Autonomous session summary + my honest assessment of your Windows storage
> health. Generated after building out the remaining spec detectors and scanning
> your live system. All findings below are from real scans run this session.

---

## TL;DR — Filesystem pressure was low; hardware health was not established

The scans established healthy free space, low metadata pressure, and low
churn/cache pressure. They did **not** establish that Disk 0, its cable, SATA
controller path, firmware, or power was healthy.

Windows Search indexing was active during one sample, but historical storage
resets and retries now provide a much stronger explanation for system stalls.

---

## What I Built This Session

I completed **Option 2** — the remaining detector families from the spec
(`viper-ssd-health.md` Section 4) plus the drive-health checks that were only
documented as "missing." Everything is read-only, test-backed, and wired to a
CLI.

### New modules (8 core + 6 CLIs)

| Area | Module | Spec |
| --- | --- | --- |
| Lean tree counter | `utils/fs_counter.py` | infra |
| Well-known target roots | `collectors/target_roots.py` | 4.4-4.7 |
| Category pressure analyzer | `analyzers/category_pressure.py` | 4.4-4.7 |
| Snapshot capture | `collectors/snapshot.py` | Sec 11 |
| Churn velocity | `analyzers/churn.py` | Sec 11, 4.4/4.5 |
| Metadata pressure composite | `analyzers/metadata_pressure.py` | 4.3 |
| Drive health / SMART / temp | `collectors/smart_data.py` | drive health |
| Process I/O | `collectors/io_processes.py` | background I/O |

New CLIs: `scan_targets`, `scan_snapshot`, `scan_metadata`, `check_smart`,
`check_io`, plus real `scripts/invoke_scan.py` / `.ps1` wrappers.

### Test coverage

- **130 tests pass** (80 prior + 50 new). Runtime ~0.8s.
- New test files: `test_fs_counter`, `test_target_roots`,
  `test_category_pressure`, `test_snapshot`, `test_churn`,
  `test_metadata_pressure`, `test_smart_data`, `test_io_processes`.

### Spec coverage now

- 4.1 Tiny-file hotspots ✅
- 4.2 Directory density ✅
- 4.3 Metadata pressure composite ✅
- 4.4 Cloud-sync churn ✅
- 4.5 Browser/WebView cache churn ✅
- 4.6 Update/installer residue ✅
- 4.7 Telemetry/log churn ✅
- Section 11 snapshot/velocity ✅
- Drive health / TRIM / free space / SMART / I/O ✅
- Maintenance mode (Sections 3, 8) — **intentionally deferred** (observe-only)

---

## Live System Findings

### Physical Drives (via `check_smart`)

| Drive | Type | Health | Severity |
| --- | --- | --- | --- |
| P3-512 | SSD (SATA) | Summary says Healthy; error evidence overrides | critical investigation |
| Samsung PSSD T7 | SSD (external) | Healthy | good |
| WD Elements 25A1 | HDD | Healthy | good |
| TOSHIBA External USB 3.0 | external | Healthy | good |

The original “overall GOOD” conclusion was wrong. The primary internal drive
reports as `P3-512`, firmware `SN18398`, on the SATA bus. The model string does
not prove a Crucial product, QLC NAND, NVMe, or DRAM-less construction.
Subsequent elevated collection exposed temperature, power-on hours, 13 read
errors, and high maximum latency; raw SMART also reported attribute 5 = 13.

### Free Space (via `check_space`, all 6 volumes)

| Drive | Total | Free | Free % | Status |
| --- | --- | --- | --- | --- |
| B: | 931 GB | 504 GB | 54.1% | GOOD |
| C: | 476 GB | 317 GB | 66.5% | GOOD |
| D: | 699 GB | 236 GB | 33.8% | GOOD |
| I: | 953 GB | 315 GB | 33.1% | GOOD |
| J: | 238 GB | 91 GB | 38.2% | GOOD |
| K: | 3726 GB | 1940 GB | 52.1% | GOOD |

**C: had 66.5% free.** That is healthy capacity headroom, but free space cannot
rule out SSD media, SATA cable, controller, firmware, power, or motherboard
faults.

### Churn / Cache / Residue (via `scan_targets --category all`)

| Category (spec) | Files | Size | Roots | Status |
| --- | --- | --- | --- | --- |
| Cloud-sync (4.4) | 16,331 | 3.01 GiB | 3 | GOOD |
| Browser/WebView (4.5) | 1,406 | 0.34 GiB | 5 | GOOD |
| Update residue (4.6) | 151 | 0.04 GiB | 2 | GOOD |
| Telemetry/log (4.7) | 1,326 | 0.06 GiB | 5 | GOOD |

All four families are **well below** warning thresholds (50k files for
cloud/browser, 10k for update/telemetry). Cloud-sync at 16k files is the
highest but still comfortably under the 50k warning line.

### Metadata Pressure (via `scan_metadata` on `C:\Users\scott\AppData`)

- Files scanned: **63,496**
- Tiny files: **32,638** (warn at 250k, critical at 500k)
- Directories: **16,627** (warn at 100k, critical at 200k)
- **Pressure score: 0/100 (GOOD)**

Your AppData — historically the worst offender for tiny-file proliferation —
is nowhere near pressure thresholds. The cleanup that motivated this project
clearly held.

### Background I/O (via `check_io`)

Top disk consumer during scanning was **`searchprotocolhost`** (Windows Search
indexing) at ~14 MB/s, followed by VS Code. This is normal, but see below.

---

## Corrected Assessment (2026-07-25)

Filesystem pressure was healthy, but the physical storage-path assessment was
incomplete and incorrect. Windows had recorded Disk 0/controller failures for
nearly three months before this report. The evidence favors the P3-512 SSD or
its immediate SATA link over a broad motherboard fault.

**For the observed slowdowns, investigate in this order:**

1. **P3-512 SSD media/controller.** Back up and replace it.
2. **SATA data cable and connector.** Replace the cable and change ports if a
  SATA replacement is used.
3. **SATA power and PSU.** Change the power connector and investigate power if
  errors persist with known-good storage.
4. **Motherboard SATA controller.** Suspect it if a known-good SATA SSD repeats
  Event 129 on the same path.

Free space, cache bloat, cloud-sync churn, and MFT pressure were not concerning.
Drive or SATA-path failure **is** concerning and takes precedence.

### Recommendation

Back up immediately, do not benchmark the P3-512, visually verify whether the
OEM board has a populated M-key M.2 2280 storage socket, and follow the tracked
replacement plan linked at the top of this report.

---

## Notes & Caveats

- **Temperature/wear unavailable this run.** `Get-StorageReliabilityCounter`
  returned no temperature — likely needs elevation or the P3 doesn't surface it
  via WMI. `check_smart` handles this gracefully; use CrystalDiskInfo for vendor
  SMART attributes if you want the raw numbers.
- **`check_io` samples one instant.** The first run caught an idle moment and
  reported no data (by design it tells you to re-run). A second run immediately
  showed the indexer. Run it 2-3× to see sustained patterns.
- **MFT/TRIM checks need admin.** I did not run `scan_mft` or `check_trim` this
  session because this VS Code instance isn't elevated. Run them from an
  elevated terminal when convenient — they're the last two data points to
  confirm a clean bill of health. TRIM in particular is worth a 5-second check.
- **Maintenance mode is deliberately absent.** Given the prior incident where an
  automated cleanup deleted VS Code's built-in extensions, the toolkit stays
  observe-only. It tells you *what* to clean; you stay in control of *whether*.

---

## Artifacts From This Session

Saved under `data/` (git-ignored):

- `data/reports/smart.json` — drive health
- `data/reports/space_{B,C,D,I,J,K}.json` — per-drive free space
- `data/reports/targets.json` — churn/cache/residue
- `data/reports/metadata_appdata.json` — metadata pressure
- `data/reports/io.json` — top I/O processes
- `data/snapshots/baseline_20260724.json` — churn baseline
- `data/reports/viper-health_quick-check_*.{json,md}` — suite quick-check

---

## Bottom Line (Corrected)

The detector implementation and its 130-test result were valid for that code
state. The “live system healthy on every metric” conclusion was not. The
original run omitted historical Windows storage-event correlation and detailed
SMART evidence. Disk 0 must now be treated as unreliable pending replacement
and post-migration observation.
