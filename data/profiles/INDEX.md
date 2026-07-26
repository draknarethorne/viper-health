# Viper Health — Machine Index

_Generated (UTC): 2026-07-26T17:56:38.084873+00:00_

One row per machine from its newest `system-health-*.json`. Fault
severity is evidence-based; capability is advisory (specs only).

| Machine | Fault | Conf. | Capability | Model | CPU | RAM | Primary drive | Bus | Wear | Free | Tiny % | Report (UTC) |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| CMIS-957903A-GT | GOOD | HIGH | CAPABLE | LENOVO 81CU | Intel Core i7-8550U CPU @ 1.80GH | 16 GiB | SAMSUNG MZVLB1T0HALR-000L2 | RAID | 0.0% | 32.2% | 50.6% | 2026-07-26 |
| CMIS-957903A-ST | CRITICAL | HIGH | UNKNOWN | STGAUBRON STGAUBRON | AMD Ryzen 5 5500 | 16 GiB | TOSHIBA External USB 3.0 | USB | 0.0% | 66.1% | ? | 2026-07-25 |

## Legend

- **Fault**: evidence-based health (GOOD/WARNING/CRITICAL) from events + storage.
- **Conf.**: collection confidence (HIGH needs elevation).
- **Capability**: advisory specs tier (SOLID/CAPABLE/DATED/WEAK) — never masks a fault.
- **Wear**: SSD wear indicator; low is good. `?` means not readable (e.g. RAID/VMD).
- **Tiny %**: tiny-file ratio from `profile_machine` (lower is better).
