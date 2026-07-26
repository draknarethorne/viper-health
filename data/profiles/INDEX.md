# Viper Health — Machine Index

_Generated (UTC): 2026-07-26T22:30:08.024674+00:00_

Layered rankings across machines. **Fault severity is health**; the
ranking score is an advisory performance & configuration aid and never
overrides a fault (WARNING/CRITICAL machines are capped).

## Layer 1 — Overall ranking (performance & configuration)

| Rank | Machine | Score | Fault | Capability | Cap. | Config | Perf | Notes |
| ---: | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | CMIS-957903A-GT | 80 | GOOD | CAPABLE | 75 | 80 | 90 |  |
| 2 | CMIS-957903A-ST | 25 | CRITICAL | UNKNOWN | — | 100 | — | fault-capped |

## Layer 2 — Per-resource spec scores

Raw specification strength per resource (0-100), independent of measured performance.

| Machine | CPU | Memory | GPU | Storage class |
| --- | ---: | ---: | ---: | ---: |
| CMIS-957903A-GT | 75 | 75 | 100 | 100 |
| CMIS-957903A-ST | — | — | — | 70 |

## Layer 3 — Storage: spec vs actual

Measured I/O throughput compared to the drive's class ceiling. Low
efficiency flags degradation or entry-tier hardware (e.g. DRAM-less).
Requires a `profile_machine --benchmark` run; otherwise `not measured`.

| Machine | Class | Seq write | Seq read | Rand write | Rand read | Efficiency | Verdict |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| CMIS-957903A-GT | NVME | 477/1000 | 986/2000 | 66/100 | 252/300 | 61% | below |
| CMIS-957903A-ST | SATA | — | — | — | — | — | not measured |

_Cells show actual/expected MB/s. Efficiency is the mean of actual÷expected._

## Layer 4 — Tuning & optimization recommendations

### CMIS-957903A-GT
- Secure Boot is disabled; enable it in UEFI for firmware-level boot integrity.
- BIOS/UEFI dates to 2020; check the vendor for firmware updates (stability, security, NVMe fixes).

## Machine details

| Machine | Fault | Conf. | Model | CPU | RAM | Primary drive | Bus | Wear | Free | Tiny % | Report (UTC) |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| CMIS-957903A-GT | GOOD | HIGH | LENOVO 81CU | Intel Core i7-8550U CPU @ 1.80GH | 15.82 GB | SAMSUNG MZVLB1T0HALR-000L2 | RAID | 0.0% | 32.1% | 49.5% | 2026-07-26 |
| CMIS-957903A-ST | CRITICAL | HIGH | STGAUBRON STGAUBRON | AMD Ryzen 5 5500 | 15.89 GB | P3-512 | SATA | 0.0% | 66.1% | ? | 2026-07-25 |

## Legend

- **Fault**: evidence-based health (GOOD/WARNING/CRITICAL) from events + storage.
- **Score**: advisory performance & configuration rank (0-100); WARNING caps at 60, CRITICAL at 25.
- **Cap./Config/Perf**: score components (capability specs, config hygiene, measured I/O).
- **Capability**: advisory specs tier (SOLID/CAPABLE/DATED/WEAK) — never masks a fault.
- **Layer 3 verdict**: meets / below / well below the drive's class expectation.
- **Wear**: SSD wear indicator; low is good. `?` means not readable (e.g. RAID/VMD).
- **Tiny %**: tiny-file ratio from `profile_machine` (lower is better).
