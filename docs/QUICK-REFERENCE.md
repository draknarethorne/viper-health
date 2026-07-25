# Viper Health Quick Reference

## Current P3-512 safety hold

The system disk `P3-512` is a 512 GB SATA SSD on Disk 0. Its vendor, NAND type,
and DRAM configuration are unknown. Retained evidence includes repeated
`storahci` Event 129 resets, Disk 0 Event 153 retries, storage bugchecks, read
errors, and reported reallocated blocks.

Until it is replaced:

- Back up irreplaceable data first.
- Do not run `benchmark_io` or `profile_machine --benchmark`.
- Do not run full-drive stress scans, extended write diagnostics, firmware
  changes, or defragmentation.
- Do not treat `HealthStatus=Healthy`, `PredictFailure=False`, green free space,
  or a healthy MFT as proof that the hardware path is healthy.
- Follow the
  [P3-512 incident and replacement plan](P3-512-INCIDENT-AND-REPLACEMENT.md).

## Safe read-only checks

### Check free space

```powershell
.venv\Scripts\python.exe -m viper_health.cli.check_space --drive C:
```

Free space describes capacity headroom. It cannot rule out media, cable,
controller, firmware, power, or motherboard faults.

### Check TRIM

Run from an elevated PowerShell terminal:

```powershell
.venv\Scripts\python.exe -m viper_health.cli.check_trim --drive C:
```

TRIM being enabled is desirable, but it does not clear an unstable disk.

### Inspect MFT health

Run from an elevated PowerShell terminal:

```powershell
.venv\Scripts\python.exe -m viper_health.cli.scan_mft --drive C:
```

MFT size and fragmentation describe NTFS metadata, not physical storage health.

### Query drive summaries

```powershell
.venv\Scripts\python.exe -m viper_health.cli.check_smart
```

Use CrystalDiskInfo or `smartctl` for vendor-aware SMART interpretation. Review
raw errors and Windows storage events together; summary status alone is not
enough.

### Identify current disk consumers

```powershell
.venv\Scripts\python.exe -m viper_health.cli.check_io --top 10
```

This is an instantaneous process-I/O sample. It cannot explain historical
controller resets by itself.

## Checks that require administrator rights

1. Start Windows Terminal or PowerShell with **Run as administrator**.
2. Change to the repository directory.
3. Run the desired command with the configured virtual environment.

```powershell
cd C:\Viper-Health
.venv\Scripts\Activate.ps1
```

Administrator rights improve access to storage reliability counters and NTFS
metadata. They do not make write-heavy diagnostics safe.

## Evidence priority

Interpret evidence in this order:

1. Data backup status and user-visible crashes or device disappearance
2. Storage-oriented bugchecks such as `0x7A` and `0x154`
3. Windows Event 129 controller resets and Event 153 disk retries
4. Raw SMART media, reallocation, pending, uncorrectable, CRC, and timeout data
5. Vendor summary status, temperature, wear, and power-on hours
6. Free space, TRIM, MFT, and filesystem-pressure metrics
7. Optional throughput measurements on known-stable storage

A lower-priority green result does not override higher-priority error evidence.

## Normal monitoring after replacement

For the first one to two weeks after migration:

- Leave the P3-512 disconnected.
- Use the replacement under ordinary workloads; do not benchmark it.
- Check Windows System logs for new Event 129, 153, 41, or storage bugchecks.
- Confirm firmware is current using the replacement vendor's utility.
- Confirm backups remain readable.
- Record a read-only machine profile without `--benchmark`.

After the storage path is proven stable, optional performance benchmarks may be
used sparingly as workload measurements. They should never be scheduled as the
primary health check.

## Related documentation

- [P3-512 incident and replacement plan](P3-512-INCIDENT-AND-REPLACEMENT.md)
- [SSD and filesystem health monitoring guide](SSD-HEALTH-MONITORING-GUIDE.md)
- [Cross-machine comparison](CROSS-MACHINE-COMPARISON.md)
- [Viper SSD health specification](../viper-ssd-health.md)
