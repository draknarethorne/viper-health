# Viper Health Comprehensive System Report

## Report identity

- **Host:** `CMIS-957903A-ST`
- **Generated (UTC):** 2026-07-25T16:41:10.991042+00:00
- **Schema:** 1
- **Mode:** observe
- **Event lookback:** 120 days

## Overall assessment

- **Severity:** CRITICAL
- **Confidence:** HIGH
- **Conclusion:** Critical fault evidence was detected; resolve concrete errors before performance testing.

> This is an evidence report, not a warranty of hardware health. Missing or
> inaccessible data remains UNKNOWN and never becomes a green result.

## Machine specifications

- **System:** STGAUBRON STGAUBRON
- **Motherboard:** STGAUBRON B450M-ST rev 1006
- **BIOS:** American Megatrends International, LLC. 5.17 (2024-12-16T00:00:00.0000000Z)
- **OS:** Microsoft Windows 11 Pro build 26200
- **Last boot:** 2026-07-25T15:48:58.5000000Z
- **Installed memory:** 15.89 GiB
- **Free memory at collection:** 8.17 GiB
- **Secure Boot:** False

### CPU

| Name | Cores / Threads | Clock | Load | Status |
| --- | ---: | ---: | ---: | --- |
| AMD Ryzen 5 5500 | 6 / 12 | 3600 / 3600 MHz | 17% | OK |

### Memory modules

| Locator | Capacity | Configured speed | Manufacturer / Part |
| --- | ---: | ---: | --- |
| DIMM 1 | 16.00 GiB | 2667 MHz | Unknown Unknown |

### Graphics

| Device | Driver | Adapter RAM | Status |
| --- | --- | ---: | --- |
| NVIDIA GeForce RTX 3050 | 32.0.16.1074 | 4.00 GiB | OK |

## Findings

| Severity | Domain | Evidence | Confidence |
| --- | --- | ---: | --- |
| CRITICAL | storage | 106 | HIGH |
| CRITICAL | system_stability | 15 | HIGH |
| CRITICAL | storage_device | 4 | HIGH |

### CRITICAL: Storage path errors or resets detected

Windows recorded 106 storage/controller event(s); concrete I/O evidence overrides green summary status.

**Recommendation:** Back up data, avoid stress tests, inspect per-disk evidence, and isolate the drive/cable/port/power path.

### CRITICAL: Unexpected shutdown or bugcheck evidence detected

Windows recorded 15 stability event(s), including 1 bugcheck report(s).

**Recommendation:** Correlate timestamps with WHEA, storage, memory, and display findings before changing hardware.

### CRITICAL: Drive evidence requires attention: P3-512

Windows reports Healthy summary status, but the combined drive severity is critical. Evidence: read errors=13, max read latency ms=9047.0, max write latency ms=4041.0, temperature C=31.0.

**Recommendation:** Back up important data and correlate this disk with Windows storage events before any benchmark or stress test.

## Storage evidence

| Disk | Bus / Media | Summary | Temperature | Wear | Read / Write errors | Max read / write latency |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| TOSHIBA External USB 3.0 | USB / Unspecified | Healthy (good) | 34.0 C | 0.0% | 0 / None | 3085.0 / 709.0 ms |
| WD Elements 25A1 | USB / HDD | Healthy (good) | 36.0 C | 0.0% | 0 / None | 5767.0 / 328.0 ms |
| P3-512 | SATA / SSD | Healthy (critical) | 31.0 C | 0.0% | 13 / None | 9047.0 / 4041.0 ms |
| Samsung PSSD T7 | USB / SSD | Healthy (good) | 0.0 C | 0.0% | None / None | 1.0 / None ms |

- **Disk space (C:):** 314.43 GiB free / 475.95 GiB total (66.1%) — GOOD
- **TRIM (C:):** Enabled, raw value 0 — GOOD
- **MFT (C:):** 1.45 GiB, 1 fragment(s) — GOOD

## Windows event evidence

- **Collection available:** True
- **Log coverage:** 2026-04-07T21:24:17.2825096Z through 2026-07-25T16:28:28.9333843Z
- **Query start:** 2026-03-27T16:41:13.0442552Z
- **Matching events:** 121
- **Event assessment:** CRITICAL

### Most recent matching events

| Time (UTC) | Provider | ID | Level | Message |
| --- | --- | ---: | --- | --- |
| 2026-07-25T15:49:25.7708136Z | EventLog | 6008 | Error | The previous system shutdown at 10:15:22 AM on ?7/?25/?2026 was unexpected. |
| 2026-07-25T15:49:01.9168397Z | Microsoft-Windows-Kernel-Power | 41 | Critical | The system has rebooted without cleanly shutting down first. This error could be caused if the system stopped responding, crashed, or lost power unexpectedly. |
| 2026-07-25T13:15:11.4034693Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-25T13:07:26.1264743Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-25T13:07:26.1264743Z | disk | 153 | Warning | The IO operation at logical block address 0x2b33a238 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-25T12:24:01.4789213Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-25T12:24:01.4789213Z | disk | 153 | Warning | The IO operation at logical block address 0x2b31f1b0 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-25T08:34:51.6908511Z | EventLog | 6008 | Error | The previous system shutdown at 5:20:19 PM on ?7/?24/?2026 was unexpected. |
| 2026-07-25T08:33:15.4047922Z | Microsoft-Windows-Kernel-Power | 41 | Critical | The system has rebooted without cleanly shutting down first. This error could be caused if the system stopped responding, crashed, or lost power unexpectedly. |
| 2026-07-24T22:22:16.8982335Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T21:18:19.6385339Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T20:36:17.8419473Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T20:01:24.3730035Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T17:39:26.3547329Z | disk | 153 | Warning | The IO operation at logical block address 0x618980 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-24T17:39:26.3530292Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T16:42:38.7861534Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T16:34:23.6054245Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T16:33:37.0522206Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T16:06:31.4094152Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T15:11:09.2916140Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T14:15:34.3944517Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-24T14:15:34.3944517Z | disk | 153 | Warning | The IO operation at logical block address 0x103746b0 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-23T21:49:55.0486394Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T20:09:36.2766654Z | EventLog | 6008 | Error | The previous system shutdown at 1:31:43 PM on ?7/?23/?2026 was unexpected. |
| 2026-07-23T20:08:23.2489693Z | Microsoft-Windows-Kernel-Power | 41 | Critical | The system has rebooted without cleanly shutting down first. This error could be caused if the system stopped responding, crashed, or lost power unexpectedly. |
| 2026-07-23T17:07:27.7604417Z | disk | 153 | Warning | The IO operation at logical block address 0x1125a210 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-23T17:07:27.7594155Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T05:10:04.3113320Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T03:02:48.7445742Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T02:45:32.8762437Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T02:29:53.6691470Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T02:28:25.3702727Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-23T00:20:19.6331475Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T21:47:13.5215027Z | disk | 157 | Warning | Disk 1 has been surprise removed. |
| 2026-07-22T20:33:20.8217914Z | disk | 153 | Warning | The IO operation at logical block address 0xd1d000 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-22T20:33:20.8207614Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T20:31:38.5875309Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T19:57:43.2938307Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T19:26:01.1066974Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T19:13:25.1397188Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T19:07:52.0875772Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T19:05:45.5672269Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T18:44:42.3888261Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T17:47:36.5898274Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T16:54:17.6653356Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T16:53:23.1428059Z | disk | 153 | Warning | The IO operation at logical block address 0x613188 for Disk 0 (PDO name: \Device\0000003c) was retried. |
| 2026-07-22T16:53:23.1418067Z | storahci | 129 | Warning | Reset to device, \Device\RaidPort0, was issued. |
| 2026-07-22T13:22:43.4477595Z | EventLog | 6008 | Error | The previous system shutdown at 3:09:13 AM on ?7/?22/?2026 was unexpected. |
| 2026-07-22T13:22:02.0517197Z | Microsoft-Windows-Kernel-Power | 41 | Critical | The system has rebooted without cleanly shutting down first. This error could be caused if the system stopped responding, crashed, or lost power unexpectedly. |
| 2026-07-22T05:33:28.5330021Z | disk | 153 | Warning | The IO operation at logical block address 0x613108 for Disk 0 (PDO name: \Device\0000003c) was retried. |

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

- Back up irreplaceable data and do not run storage benchmarks or write-heavy diagnostics until storage evidence is resolved.
- Correlate each crash timestamp with storage, WHEA, memory, display, and power evidence; a Kernel-Power event alone does not identify the cause.
- Use active benchmarks only on known-stable, backed-up hardware after passive preflight finds no unresolved fault evidence.

## AI review guidance

When evaluating this report, prioritize concrete event and error evidence over
summary labels. Correlate timestamps across domains, distinguish absent evidence
from unavailable collection, and do not recommend stress tests when storage, WHEA,
memory, power, or crash evidence is unresolved.
