# Cross-Machine SSD/Filesystem Comparison

Compare storage health across your machines (e.g. **laptop vs desktop**) using
git as the transport. Each machine captures a *profile* JSON and commits it;
any machine can then diff two profiles to see exactly why one feels faster.

This workflow is **read-only** (observe mode). The optional `--benchmark` flag
writes and deletes a small temporary file to measure I/O.

---

## TL;DR

```bash
# 1. On EACH machine (laptop, desktop):
python -m viper_health.cli.profile_machine --benchmark
git add data/profiles/<HOSTNAME>.json
git commit -m "profile: <machine> storage snapshot"
git push

# 2. On ANY machine, after `git pull`:
python -m viper_health.cli.compare_baseline \
    --baseline data/profiles/DESKTOP.json \
    --current  data/profiles/LAPTOP.json \
    --verbose
```

`--baseline` is your **reference** machine; `--current` is the machine you're
evaluating *against* it. The report shows how `--current` differs.

---

## Step 1 — Capture a profile on each machine

Run this on every machine you want to compare. It writes
`data/profiles/<HOSTNAME>.json`.

```bash
# Default: scans your user home, no benchmark
python -m viper_health.cli.profile_machine

# Recommended: include the I/O benchmark for full comparison
python -m viper_health.cli.profile_machine --benchmark

# Scan a specific root and show progress on large trees
python -m viper_health.cli.profile_machine C:/Users/scott --benchmark --progress
```

Useful flags:

| Flag | Purpose |
| --- | --- |
| `--benchmark` | Include sequential/random read+write throughput (writes a temp file) |
| `--benchmark-size <MB>` | Benchmark test-file size (default 100) |
| `--drive C:` | Drive inspected for free space + TRIM |
| `--no-drives` / `--no-trim` | Skip privileged collectors (faster) |
| `--exclude <path/glob>` | Prune paths from the walk (repeatable) |
| `--progress` | Live progress during the scan |

> **Tip:** For the most complete drive data (wear / TBW / power-on hours), run
> from an **elevated** terminal. On drives behind Intel RST / VMD, SMART
> passthrough may still be blocked — see `check_smart` output for guidance.

### Commit the profile

```bash
git add data/profiles/<HOSTNAME>.json
git commit -m "profile: <machine> storage snapshot"
git push
```

Each machine has a distinct filename (its hostname), so profiles never collide.

---

## Step 2 — Compare two machines

On any machine, pull the latest profiles and diff them:

```bash
git pull
python -m viper_health.cli.compare_baseline \
    --baseline data/profiles/DESKTOP.json \
    --current  data/profiles/LAPTOP.json \
    --verbose
```

The comparison highlights differences across shared metrics:

- **Health score** — overall filesystem health (higher is better)
- **Tiny-file count / ratio** — small-file burden (lower is better)
- **Free space %** — SSD headroom for GC/SLC cache (higher is better)
- **Benchmark throughput** — per-test MB/s, if both profiles ran `--benchmark`

Severity is derived from percentage deltas:

| Metric | Warning | Critical |
| --- | --- | --- |
| Health score | −10% | −20% |
| Tiny-file count / ratio | +25% | +50% |
| Free space % | −15% | −30% |
| Benchmark throughput | −10% | −20% |

---

## Interpreting results (laptop vs desktop)

A machine can feel slower even with *better hardware*. The usual culprits,
surfaced by this comparison, are:

1. **Tiny-file / metadata pressure** — a much higher `tiny_files` / `tiny_file_ratio`
   on one machine crushes random I/O regardless of drive age.
2. **Low free space** — under ~20% free, SSD garbage collection and SLC cache
   suffer; `free_percent` will flag it.
3. **Drive class / bus** — check each profile's `drives[].bus_type` and
   `media_type`. A DRAM-less QLC drive, or one behind RAID (Intel RST / VMD),
   behaves differently from a simpler SATA/DRAM SSD.
4. **Benchmark deltas** — if random-write throughput is far lower on the slow
   machine, that points at metadata pressure or a weaker drive.

If the slower machine shows high tiny-file pressure, that's **fixable
filesystem state**, not failing hardware. Target the hotspots reported by:

```bash
python -m viper_health.cli.suite --preset full-system --progress --console-summary
python -m viper_health.cli.scan_metadata
```

---

## Profile schema (v1)

Top-level keys used for comparison are intentionally flat so `compare_baseline`
can diff them directly:

```jsonc
{
  "schema_version": 1,
  "profile_type": "machine_profile",
  "timestamp": "2026-07-24T...Z",
  "machine": { "hostname": "...", "os": "...", "cpu_count": 8, ... },
  "scan_root": "C:/Users/scott",
  "elevated": true,

  "free_percent": 32.9,
  "total_files": 363587,
  "tiny_files": 12345,
  "tiny_file_ratio": 3.40,
  "directories_scanned": 59091,
  "findings_count": 0,
  "health_score": { "overall_score": 100.0, "severity_band": "good" },

  "disk_space": { "...": "..." },
  "drives":     [ { "bus_type": "...", "media_type": "...", "...": "..." } ],
  "trim":       { "...": "..." },
  "benchmark_results": [ { "test_name": "...", "throughput_mb_s": 0.0, "severity": "..." } ]
}
```

Unavailable sections (missing PowerShell, non-admin, unsupported hardware) are
recorded as `{ "available": false, "error": "..." }` instead of failing the run.
