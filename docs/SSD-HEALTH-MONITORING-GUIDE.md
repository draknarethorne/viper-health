# SSD and Filesystem Health Monitoring Guide

## Purpose

Viper Health measures several distinct layers of storage behavior:

- filesystem pressure, including tiny files and directory density
- churn in cloud, browser, update, and telemetry locations
- NTFS metadata size and fragmentation
- free-space and TRIM state
- Windows drive-summary and reliability counters
- process I/O and optional performance measurements
- baseline and snapshot changes over time

These layers complement one another, but they are not interchangeable. Healthy
free space, TRIM, MFT, or filesystem pressure does not certify an SSD, cable,
controller, firmware, power supply, or motherboard.

## Current P3-512 incident

The installed system disk identifies as `P3-512`, firmware `SN18398`, and
Windows reports it as a 512 GB **SATA** SSD on Disk 0. The model string does not
establish its vendor, NAND type, or DRAM configuration.

The earlier Crucial P3 / NVMe / QLC identification was incorrect. Retained
Windows evidence includes:

- 75 `storahci` Event 129 resets targeting `RaidPort0`
- 21 Disk 0 Event 153 I/O retries
- storage bugchecks `0x154` and `0x7A`
- 13 total read errors
- raw SMART attribute 5 value of 13
- maximum observed read and write latency measured in seconds

The first retained storage reset occurred on 2026-04-30, nearly three months
before the benchmark-enabled profile crash. The benchmark did not create the
underlying fault, but sustained I/O likely provoked the unstable path.

Do not benchmark or stress the P3-512. See the
[P3-512 incident and replacement plan](P3-512-INCIDENT-AND-REPLACEMENT.md).

## Evidence model

Use this order when assessing a machine:

1. Backup status and user-visible symptoms
2. Storage-oriented bugchecks and unexpected shutdowns
3. Controller resets and disk retries in the Windows System log
4. Raw media, reallocation, pending, uncorrectable, CRC, and timeout counters
5. Vendor summary status, temperature, wear, and power-on hours
6. Free space, TRIM, MFT, and filesystem-pressure metrics
7. Optional performance results on known-stable storage

A lower-priority green result cannot override higher-priority error evidence.
For example, `HealthStatus=Healthy` is a firmware/driver summary threshold; it
can coexist with meaningful read errors, retries, and controller resets.

## Toolkit coverage

| Area | Tool | Scope |
| --- | --- | --- |
| Tiny-file hotspots | `scan_tiny_files` | Filesystem pressure |
| Directory density | `scan_directory_density` | Filesystem pressure |
| Composite metadata pressure | `scan_metadata` | Filesystem and optional MFT signals |
| Churn/cache categories | `scan_targets` | Cloud, browser, update, telemetry |
| Snapshot velocity | `scan_snapshot` | Change over time |
| MFT health | `scan_mft` | NTFS metadata |
| TRIM | `check_trim` | OS delete-notification state |
| Free space | `check_space` | Capacity headroom |
| Drive summary | `check_smart` | Windows Storage counters |
| Active process I/O | `check_io` | Current process activity |
| Machine profile | `profile_machine` | Cross-machine facts |
| Baseline comparison | `compare_baseline` | Metric deltas |
| I/O benchmark | `benchmark_io` | Optional workload measurement |

## Known gaps

### Windows storage-event integration

Normal reports do not yet automatically collect and score Event 129, Event 153,
Kernel-Power events, or bugcheck payloads. This is a critical gap because the
P3-512 incident demonstrated that filesystem metrics and summary SMART status
can look green while the operating system repeatedly resets the storage path.

### Raw vendor SMART interpretation

Windows Storage cmdlets expose useful counters but do not fully interpret every
vendor-specific SATA or NVMe attribute. Use CrystalDiskInfo or `smartctl` to
review:

- reallocated sectors or blocks
- pending and offline-uncorrectable sectors
- reported uncorrectable errors
- command timeouts
- SATA UDMA CRC errors
- unsafe shutdowns or unexpected power loss
- percentage used and total host writes

### Benchmark preflight

`benchmark_io` and `profile_machine --benchmark` now fail closed unless the
Windows System event query and physical-drive reliability counters are
available and show no unresolved warning or critical evidence. Storage resets,
disk retries, bugchecks, WHEA events, drive errors, unknown drive severity, or
missing critical coverage block the write workload. There is no override.

Passing preflight means only that the required passive evidence did not block
the measurement. It does not certify hardware health.

## Benchmark safety policy

A benchmark is a workload measurement, not a drive-health test. Do not run one
when any of the following is true:

- important data is not backed up
- Windows recently logged Event 129 or Event 153
- the system had a storage-oriented bugcheck or unexplained reset
- SMART or reliability counters show media, read, reallocation, pending,
  uncorrectable, CRC, or timeout errors
- the drive recently disappeared from firmware or entered BIOS unexpectedly
- the machine is the affected P3-512 system

Even on known-stable storage, use benchmarks sparingly and never interpret a
high throughput score as proof of hardware health.

## Recommended monitoring workflow

### Weekly read-only checks

```powershell
.venv\Scripts\python.exe -m viper_health.cli.check_space --drive C:
.venv\Scripts\python.exe -m viper_health.cli.scan_targets --category all
.venv\Scripts\python.exe -m viper_health.cli.check_smart
```

Also review Windows System events for new controller resets, disk retries, and
unexpected shutdowns.

### Monthly trend checks

```powershell
.venv\Scripts\python.exe -m viper_health.cli.scan_mft --drive C:
.venv\Scripts\python.exe -m viper_health.cli.scan_snapshot capture --output data\snapshots\month.json
.venv\Scripts\python.exe -m viper_health.cli.profile_machine --output data\profiles\current.json
```

Do not add `--benchmark` unless storage is known-stable, backed up, and clear of
recent error evidence.

### After cleanup or heavy writes

Allow idle time for TRIM, garbage collection, and dynamic cache recovery. Then
compare read-only snapshots and normal application behavior. Do not force a
before/after benchmark when investigating suspected hardware instability.

## Troubleshooting slow or stalled storage

1. Back up important data.
2. Check Event 129, Event 153, Kernel-Power, and bugcheck history.
3. Review detailed SMART and Windows reliability counters.
4. If errors target one SATA disk, replace its data cable and change its SATA
   port and power connector after the data is safe.
5. Test with a known-good replacement disk under ordinary workloads.
6. Investigate motherboard, PSU, RAM, BIOS, and PCIe only if errors persist with
   the suspect disk and link removed.
7. Use process-I/O sampling to identify background load only after hardware-path
   errors have been addressed.
8. Use free-space, TRIM, MFT, and filesystem scans to optimize a stable system,
   not to dismiss controller or media failures.

## Interpreting common findings

### Low free space

Low free space can reduce SSD cache headroom and increase garbage-collection
work. It cannot cause the controller to report a healthy disk if media errors
exist, nor does abundant free space rule out failure.

### High tiny-file or directory pressure

Metadata pressure can increase random-I/O cost and application latency. It does
not explain SATA controller resets, disk retries, device disappearance, or
storage bugchecks by itself.

### Active search indexing

Search indexing can produce legitimate background I/O. A healthy storage path
must tolerate it. Indexing may expose a marginal device but does not explain
months of controller resets as a software-only issue.

### Green SMART summary

Treat green summary status as one data point. Firmware thresholds are designed
to declare predicted failure, not to guarantee error-free operation.

## Replacement acceptance criteria

After replacement:

- keep the P3-512 disconnected for initial validation
- use ordinary workloads for one to two weeks
- verify no new Event 129/153 or storage bugchecks appear
- update replacement SSD firmware using its vendor utility
- verify backups and restored data
- capture a read-only machine profile without `--benchmark`

If the machine is stable on NVMe, the fault was within the old SATA path. If a
known-good SATA disk repeats Event 129, investigate the SATA cable, port,
controller, power connector, and PSU. If failures continue with SATA removed,
expand the investigation to motherboard, PCIe, RAM, BIOS, and power.

## Related documentation

- [P3-512 incident and replacement plan](P3-512-INCIDENT-AND-REPLACEMENT.md)
- [Quick reference](QUICK-REFERENCE.md)
- [Cross-machine comparison](CROSS-MACHINE-COMPARISON.md)
- [Authoritative specification](../viper-ssd-health.md)
