# Comprehensive System Health Reports

## Purpose

`system_report` produces a paired JSON and Markdown snapshot of passive Windows
health evidence. The JSON preserves structured facts for scripts and AI; the
Markdown summarizes the same evidence for review and Git diffs.

The report covers:

- computer, motherboard, BIOS/UEFI, operating-system, CPU, memory, GPU, TPM,
  Secure Boot, battery, and ACPI thermal-zone facts
- physical-drive summaries and reliability counters
- mounted volumes, free space, TRIM, and NTFS MFT state
- retained Windows System events for storage, unexpected shutdowns, bugchecks,
  WHEA hardware errors, memory diagnostics, and display-driver recovery
- optional filesystem-pressure results when a root is explicitly requested
- collection availability, log retention coverage, confidence, findings, and
  recommendations

No benchmark, stress test, reboot, firmware operation, cleanup, or mutation is
performed by this command.

## Privacy and data handling

> **Privacy note:** The collector deliberately excludes serial numbers, system
> UUIDs, user names, network addresses, and MAC addresses. Windows event
> messages can still contain volume labels, device paths, or other local names.
> Review generated reports before pushing them to a public repository.

## Generate a report

Run from an elevated PowerShell terminal for the best storage and event
coverage:

```powershell
.venv\Scripts\python.exe -m viper_health.cli.system_report --lookback-days 120
```

Default outputs are written beneath a per-host directory:

```text
data/profiles/<HOSTNAME>/system-health-<UTC-TIMESTAMP>.json
data/profiles/<HOSTNAME>/system-health-<UTC-TIMESTAMP>.md
```

Comprehensive system-health reports use schema version 1. The separate
`profile_machine` cross-machine profile format uses schema version 2; the two
formats have different structures and should not be compared as if they were
the same schema.

Useful options:

| Option | Purpose |
| --- | --- |
| `--lookback-days N` | Event-query window; default 90 days |
| `--drive C:` | Volume used for free-space, TRIM, and MFT checks |
| `--output-dir PATH` | Directory for both generated artifacts |
| `--output-json PATH` | Explicit JSON path |
| `--output-md PATH` | Explicit Markdown path |
| `--filesystem-root PATH` | Opt into a read-only tiny-file/density scan |
| `--exclude PATH` | Exclude a path/glob from an optional filesystem scan |
| `--no-events` | Skip event collection and report coverage as unavailable |
| `--no-storage` | Skip storage collection and report coverage as unavailable |
| `--fail-on-critical` | Return exit code 2 after writing a critical report |

`--output-dir` changes the base directory used for automatic per-host names.
Explicit `--output-json` and `--output-md` paths override the corresponding
automatic path entirely.

Skipping a section never turns it green. It is recorded as unavailable and
reduces assessment confidence.

## Evidence hierarchy

Interpret the report in this order:

1. explicit bugchecks, storage retries/resets, WHEA faults, and diagnostic errors
2. raw drive error/reliability counters
3. repeated unexpected shutdowns and component recoveries
4. vendor summary health, temperature, wear, and runtime state
5. capacity, TRIM, MFT, and filesystem-pressure facts
6. optional performance measurements from known-stable systems

The report intentionally has no universal numeric score. A weighted score can
hide a critical event behind unrelated green metrics.

## Event families

The collector uses provider and event identifiers for primary classification so
localized message text is not required.

| Domain | Providers / event IDs |
| --- | --- |
| Storage | `storahci`, `stornvme`, `disk`, `Ntfs`; 7, 51, 55, 98, 129, 140, 153, 157 |
| Stability | Kernel-Power 41, WER-SystemErrorReporting 1001, EventLog 6008 |
| WHEA | WHEA-Logger 1, 17, 18, 19, 20, 46, 47 |
| Memory | MemoryDiagnostics-Results 1101, 1201 |
| Display | Display / Display-Driver 4101 |

Informational NTFS Event 98 records stating that a volume is healthy are
excluded. The report records the oldest and newest retained System-log entries,
the requested query start, and the matching event count. “No matching events”
is meaningful only when collection and retention coverage are available.

## Git transport and multi-machine use

A practical workflow on each machine is:

```powershell
git pull --ff-only
.venv\Scripts\python.exe -m viper_health.cli.system_report --lookback-days 90
git add data/profiles/<HOSTNAME>/
git commit -m "profile: update <HOSTNAME> system health"
git push
```

Keep timestamped reports to evaluate trends and retain incident evidence. Use
Git diffs or provide two JSON/Markdown pairs to AI. When comparing machines,
normalize for:

- different event-log retention windows
- different report lookback periods
- elevation and unavailable collectors
- laptop versus desktop power/thermal behavior
- direct SATA/NVMe versus USB/RAID/VMD storage paths
- hardware class, workload, and uptime

Do not compare raw event counts without also comparing coverage duration.
For the dedicated profile comparison workflow, see
[Cross-Machine Comparison](CROSS-MACHINE-COMPARISON.md).

## Benchmark and stress-test policy

`benchmark_io` and `profile_machine --benchmark` run mandatory passive preflight
first. They fail closed when:

- System event coverage is unavailable
- drive reliability counters are unavailable
- a warning/critical storage, stability, WHEA, memory, or display event exists
- a drive has warning, critical, or unknown severity
- drive read/write errors are nonzero

There is no override. Passing preflight does not certify hardware health; it
only permits an optional comparative measurement. Absolute throughput does not
identify NAND type, dedicated DRAM, cache exhaustion, temperature, or failure.

## Other component diagnostics

Some useful diagnostics cannot be safely or reliably automated as routine
health checks:

| Component | Diagnostic | Why it is not automatic |
| --- | --- | --- |
| Memory | Windows Memory Diagnostic or MemTest86 | Requires a reboot/boot media and exclusive memory access |
| CPU | Vendor diagnostics, OCCT, Prime95 | Sustained thermal/electrical stress; performance is not a fault verdict |
| GPU | OCCT, 3DMark, vendor tools | Heavy power/thermal load and vendor-specific interpretation |
| SSD/HDD | Vendor extended self-test or `smartctl` long test | Can add sustained I/O and may be unsafe on a failing device |
| PSU | Known-good PSU substitution or electrical testing | Software cannot directly validate rails, ripple, or transient response |
| Cooling | HWiNFO sensor logging under normal workload | Generic ACPI thermal zones often do not expose CPU/GPU package sensors |

Use these only after backups are current and passive evidence has identified a
specific question. Never schedule stress tests as the primary health monitor.

## AI review prompt

A useful prompt when attaching the generated files is:

> Analyze this Viper Health report using the evidence hierarchy. Separate
> concrete faults from summary status, correlate timestamps across domains,
> account for log coverage and unavailable sections, identify changes from the
> previous report, and do not recommend stress tests while fault evidence is
> unresolved.

## Current-machine validation

The first report generated on 2026-07-25 successfully detected the known
P3-512 incident without a filesystem sweep or benchmark. It retained complete
machine specifications, counted storage and stability evidence, ignored
informational healthy-volume events, and preserved USB maximum latency as
context without diagnosing USB drives from that value alone.
