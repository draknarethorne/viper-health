# Viper Health Comprehensive System Report

## Report identity

- **Host:** `CMIS-957903A-GT`
- **Generated (UTC):** 2026-07-26T17:56:28.369628+00:00
- **Schema:** 1
- **Mode:** observe
- **Event lookback:** 120 days

## Overall assessment

- **Severity:** GOOD
- **Confidence:** HIGH
- **Conclusion:** No fault findings were detected in the evidence successfully collected.

> This is an evidence report, not a warranty of hardware health. Missing or
> inaccessible data remains UNKNOWN and never becomes a green result.

## Machine specifications

- **System:** LENOVO 81CU
- **Motherboard:** LENOVO LNVNB161216 rev SDK0R32862 WIN
- **BIOS:** LENOVO 7KCN33WW(V1.14) (2020-12-29T00:00:00.0000000Z)
- **OS:** Microsoft Windows 11 Pro build 26200
- **Last boot:** 2026-07-19T05:31:59.9000230Z
- **Installed memory:** 15.82 GiB
- **Free memory at collection:** 5.43 GiB
- **Secure Boot:** False

### CPU

| Name | Cores / Threads | Clock | Load | Status |
| --- | ---: | ---: | ---: | --- |
| Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz | 4 / 8 | 1800 / 2001 MHz | 26% | OK |

### Memory modules

| Locator | Capacity | Configured speed | Manufacturer / Part |
| --- | ---: | ---: | --- |
| ChannelA-DIMM0 | 8.00 GiB | 2400 MHz | Samsung M471A1K43BB1-CTD |
| ChannelB-DIMM0 | 8.00 GiB | 2400 MHz | Samsung M471A1K43CB1-CTD |

### Graphics

| Device | Driver | Adapter RAM | Status |
| --- | --- | ---: | --- |
| NVIDIA GeForce GTX 1050 | 32.0.15.7688 | 4.00 GiB | OK |
| Intel(R) UHD Graphics 620 | 26.20.100.6913 | 1.00 GiB | OK |

## Machine capability (advisory)

> Advisory only. This capability rating reflects specifications and is
> intentionally separate from the fault severity above — it never
> upgrades or masks concrete fault evidence.

- **Overall capability:** CAPABLE
- **Summary:** LENOVO 81CU is a capable machine for mainstream workloads (CPU: capable, memory: capable, GPU: solid).

| Component | Tier | Notes |
| --- | --- | --- |
| cpu | CAPABLE | Intel Core i7 generation 8 is serviceable but a few generations behind current. |
| memory | CAPABLE | — |
| gpu | SOLID | — |
| os_firmware | SOLID | — |
| form_factor | CAPABLE | Battery present — this is a laptop; thermal and power limits cap sustained performance. |

**Optimization recommendations:**

- Secure Boot is disabled; enable it in UEFI for firmware-level boot integrity.
- BIOS/UEFI dates to 2020; check the vendor for firmware updates (stability, security, NVMe fixes).

## Findings

No fault findings were detected in the evidence that was successfully collected.

## Storage evidence

| Disk | Bus / Media | Summary | Temperature | Wear | Read / Write errors | Max read / write latency |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| SAMSUNG MZVLB1T0HALR-000L2 | RAID / SSD | Healthy (good) | 1.0 C | 0.0% | None / None | 231.0 / 280.0 ms |
| TOSHIBA External USB 3.0 | USB / Unspecified | Healthy (good) | 29.0 C | 0.0% | 0 / None | 1924.0 / 1921.0 ms |

- **Disk space (C:):** 307.07 GiB free / 952.62 GiB total (32.2%) — GOOD
- **TRIM (C:):** Enabled, raw value 0 — GOOD
- **MFT (C:):** 1.87 GiB, 1 fragment(s) — GOOD

## Windows event evidence

- **Collection available:** True
- **Log coverage:** 2026-06-17T20:11:43.0274137Z through 2026-07-26T17:34:19.2287586Z
- **Query start:** 2026-03-28T17:56:31.1127988Z
- **Matching events:** 0
- **Event assessment:** INFO

## Collection status

| Section | Available | Error / limitation |
| --- | --- | --- |
| system_inventory | True | None |
| event_log | True | None |
| physical_drives | True | None |
| disk_space | True | None |
| volumes | True | None |
| trim | True | None |
| mft | True | None |

## Recommendations

- Retain this report as a baseline and compare future event counts and hardware facts after normal use.
- Use active benchmarks only on known-stable, backed-up hardware after passive preflight finds no unresolved fault evidence.

## AI review guidance

When evaluating this report, prioritize concrete event and error evidence over
summary labels. Correlate timestamps across domains, distinguish absent evidence
from unavailable collection, and do not recommend stress tests when storage, WHEA,
memory, power, or crash evidence is unresolved.
