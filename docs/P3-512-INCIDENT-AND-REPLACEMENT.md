# P3-512 Storage Incident and Replacement Plan

**Assessment date:** 2026-07-25
**Affected system:** STGAUBRON / B450M-ST (revision 1006), Ryzen 5 5500
**Affected system disk:** Disk 0, `P3-512`, firmware `SN18398`, 512 GB SATA SSD

> **Safety status:** Treat the current Disk 0 storage path as unreliable. Back up
> irreplaceable data before troubleshooting. Do not run I/O benchmarks, extended
> write tests, full-drive stress scans, defragmentation, or firmware changes on
> the P3-512.

## Executive recommendation

1. Back up critical data to known-good external storage.
2. Physically inspect the motherboard before buying an NVMe drive. Windows
   firmware tables report an `U3700 M.2 Slot`, but an OEM board may omit the
   physical connector, standoff, PCIe wiring, or boot support.
3. If a complete M-key M.2 2280 NVMe position is present, install a 1 TB or 2 TB
   TLC SSD with dedicated DRAM, preferably a WD_BLACK SN850X or Samsung 990 PRO.
4. If no usable NVMe position exists, install a Samsung 870 EVO 1 TB or 2 TB
   2.5-inch SATA SSD using a **new SATA data cable**, a different motherboard
   SATA port, and preferably a different SATA power connector.
5. Prefer a clean Windows installation. Disconnect the P3-512 during the first
   boot and installation so firmware cannot select the wrong boot device.
6. After migration, use the machine normally for one to two weeks without
   benchmarks and monitor Windows System events for new Event 129, 153, 41,
   `0x154`, or `0x7A` records.

## Corrections to the earlier assessment

The 2026-07-24 report incorrectly identified `P3-512` as a Crucial P3 NVMe QLC
SSD. Live Windows inventory instead reports:

- `FriendlyName`: `P3-512`
- `BusType`: `SATA`
- Disk number: 0
- Firmware: `SN18398`
- Parent controller: AMD `1022:43C8`, identified as a **400 Series Chipset SATA
  Controller**
- Driver path: Microsoft `storahci`

The model string alone does not identify the SSD vendor, NAND type, or whether
it has dedicated DRAM. Claims that it is Crucial, NVMe, QLC, or DRAM-less are
therefore unsupported and have been removed from current documentation.

Green free-space, TRIM, MFT, and filesystem-pressure results remain valid for
their narrow scopes. They do **not** establish physical-drive or controller
health. Windows had already logged storage resets before the July 24 analysis.

## Evidence collected

### Retained event history

The retained Windows System log begins on 2026-04-07. The first matching
storage failure is 2026-04-30 at 16:57:37:

- `storahci` Event 129: reset issued to `\Device\RaidPort0`
- Disk Event 153: Disk 0 I/O operation retried

From 2026-04-30 through 2026-07-25, the retained log contains:

- 75 `storahci` Event 129 controller resets, all targeting `RaidPort0`
- 21 Disk 0 Event 153 I/O retries
- a pronounced increase in July (51 resets and 11 Disk 0 retries)

Unexpected shutdowns include storage-oriented bugchecks:

- `0x154` — `UNEXPECTED_STORE_EXCEPTION`
- `0x7A` — `KERNEL_DATA_INPAGE_ERROR`

The latest crash occurred during a benchmark-enabled machine profile. The
benchmark did not create the underlying fault—the event history predates the
tool by months—but sustained I/O likely provoked the unstable path.

### Current device telemetry

Windows currently reports the P3-512 as globally `Healthy` and
`PredictFailure=False`, but deeper counters show:

- 13 total read errors
- raw SMART attribute 5 value of 13 (reported as reallocated sectors/blocks by
  the standard Windows SMART layout)
- maximum observed read latency of about 9 seconds
- maximum observed write latency of about 4 seconds
- 6,797 power-on hours

SMART threshold status is not a clean bill of health. A disk can cause timeouts,
controller resets, and crashes before its firmware crosses a vendor failure
threshold.

### Evidence about the broader platform

- No retained WHEA hardware-error events were found.
- CPU, GPU, PCIe root ports, SATA controllers, and external disks currently
  enumerate normally.
- The failures concentrate on Disk 0 / `RaidPort0`.
- The board has two native AMD `1022:7901` SATA functions plus the active
  `1022:43C8` 400-Series chipset SATA controller used by the P3-512.

This evidence favors the SSD or its immediate SATA link over a broad
motherboard failure, but software cannot completely distinguish among the SSD,
SATA data cable, SATA power, individual SATA port, chipset controller, and power
supply.

## Likely cause order

1. P3-512 SSD
2. SATA data cable or connector
3. SATA power connector
4. Individual SATA port / 400-Series SATA controller path
5. Power-supply instability
6. Broad motherboard failure

The SSD is the leading suspect because the errors target only its path and it
reports read errors/reallocated blocks. A missing SMART attribute 199 means SATA
CRC history is unavailable, so the cable remains a meaningful possibility.

## What an M.2 NVMe connector looks like

Do not look for a cable socket. An M.2 SSD plugs directly into a small,
low-profile edge-card socket lying flat on the motherboard.

A normal M.2 2280 storage position has **both** of these parts:

1. **Socket:** approximately 22 mm (0.87 in) wide, usually labeled `M.2`,
   `M2_1`, `M2`, `SSD`, or similar. It resembles a thin horizontal slot with a
   plastic body and closely spaced metal contacts.
2. **Hold-down point:** a threaded standoff or screw hole approximately 80 mm
   (3.15 in) away from the socket, often labeled `2280` or `80`. Intermediate
   holes may be labeled `2242` or `2260`.

An M.2 2280 SSD is a narrow circuit board 22 mm wide and 80 mm long. It is
inserted into the socket at roughly a 20–30 degree angle, lowered until flat,
and secured at the far end with one small screw.

### Pins and keying

- The M.2 edge-connector standard has **75 positions and up to 67 electrical
  contacts** at 0.5 mm pitch.
- Do not count contacts to identify it; they are tiny and split between both
  sides of the SSD.
- A typical NVMe x4 SSD is **M-keyed**: its gold edge has one notch near the
  right side when the component label faces up.
- Some SATA or PCIe x2 M.2 drives are B-key or B+M-key, with a different notch
  or two notches.
- A short 22 × 30 mm M.2 socket populated with a Wi-Fi/Bluetooth card and two
  antenna wires is **not** the storage position. Firmware reports both an
  `M.2 WLAN/BT slot` and a separate `U3700 M.2 Slot` on this machine.

### Visual references

These pages include useful photographs and keying diagrams:

- [Dell: M.2 cards, motherboard slots, keys, sizes, and types](https://www.dell.com/support/kbdoc/en-us/000144170/how-to-distinguish-the-differences-between-m-2-cards)
- [Wikipedia: M.2 form factors, M-key/B-key diagram, connector photo, and dimensions](https://en.wikipedia.org/wiki/M.2#Form_factors_and_keying)
- [ASUS: motherboard SATA/M.2 hardware inspection and installation examples](https://www.asus.com/support/faq/1044083/)

Dell's article is the best first visual reference: it includes an explicit
photo labeled **“M.2 Slot on Motherboard”** and comparisons of 2280 SATA and
NVMe cards.

## How to inspect this OEM board

1. Shut Windows down completely.
2. Turn off and unplug the power supply. Hold the case power button for several
   seconds after unplugging.
3. Photograph the entire motherboard before moving anything.
4. Look between the CPU socket and the main PCIe graphics-card slot.
5. Look below or behind the graphics card; the card may conceal the connector.
6. Look between the lower PCIe slots and near the chipset heatsink.
7. Search the silkscreen for `U3700`, `M.2`, `M2`, `SSD`, `2242`, `2260`, or
   `2280`.
8. Confirm that a real socket is soldered to the board—not merely an empty
   rectangular outline or unused solder pads.
9. Confirm there is an 80 mm mounting standoff or threaded hole.
10. Confirm the socket is M-keyed and intended for storage, not the short Wi-Fi
    position.
11. Check the opposite side of the board only if the chassis design allows it;
    some OEM systems place M.2 connectors on the rear.
12. If the socket is under the GPU, remove the GPU only after documenting its
    cabling and following anti-static precautions.

### What an omitted OEM connector looks like

An OEM may reuse a board design but omit components. You may see:

- white text or an outline marked `U3700` or `M.2`
- rows of exposed solder pads where the socket would have been
- mounting-hole labels but no socket
- a socket but no threaded standoff

Any of those means firmware inventory alone is insufficient. **Do not buy an
NVMe drive until a populated storage socket and 2280 hold-down point are
visually confirmed.** A clear, well-lit photograph can be compared with the
Dell reference above or reviewed by a repair shop.

## Replacement choices

### Preferred if M.2 NVMe is physically confirmed

#### WD_BLACK SN850X

- 1 TB model: `WDS100T2X0E` (without heatsink)
- M.2 2280, PCIe 4.0 x4; explicitly backward-compatible with PCIe 3.0
- TLC 3D NAND
- dedicated DDR4 DRAM
- 600 TBW and five-year limited warranty at 1 TB

References:

- [WD_BLACK SN850X official product page](https://www.sandisk.com/products/ssd/internal-ssd/wd-black-sn850x-nvme-ssd)
- [SN850X architecture/specification review](https://www.tomshardware.com/reviews/wd-black-sn850x-ssd-review-back-in-black)

#### Samsung 990 PRO

- 1 TB model: `MZ-V9P1T0BW` (without heatsink)
- M.2 2280, PCIe 4.0 x4
- Samsung TLC V-NAND
- dedicated LPDDR4 DRAM
- 600 TBW and five-year limited warranty at 1 TB

References:

- [Samsung 990 PRO product family](https://www.samsung.com/us/computing/memory-storage/solid-state-drives/)
- [990 PRO architecture/specification review](https://www.tomshardware.com/reviews/samsung-990-pro-ssd-review)

A PCIe 4.0 drive should negotiate down to the platform's supported generation.
The Ryzen 5 5500/B450 system will not reach Gen4 headline speeds, but the drive
remains suitable for a future platform upgrade.

### Preferred SATA fallback

#### Samsung 870 EVO

- 1 TB model: `MZ-77E1T0B/AM`
- 2.5-inch SATA 6 Gb/s
- Samsung 3-bit V-NAND (TLC)
- dedicated 1 GB LPDDR4 DRAM at 1 TB
- Samsung MKX controller
- five-year limited warranty; 600 TBW at 1 TB

Reference: [Samsung 870 EVO specifications](https://www.samsung.com/us/computing/memory-storage/solid-state-drives/870-evo-sata-2-5-ssd-1tb-mz-77e1t0b-am/)

The SATA fallback is slower than NVMe but is a substantial quality and
reliability upgrade over an unidentified OEM SSD. Use a new cable and different
port/power connector to avoid carrying a link fault forward.

## Migration plan

### Before opening the case

- Copy documents, source repositories, credentials, encryption recovery keys,
  browser exports, and other irreplaceable data first.
- Verify backup files by opening a sample from the destination.
- Create Windows installation media on a known-good USB device.
- Record application licenses and account recovery information.
- C: is currently not BitLocker-encrypted, but re-check before migration.

### Preferred clean-install path

1. Install the new SSD.
2. Disconnect the P3-512 SATA data cable.
3. Install Windows onto the new SSD.
4. Install current AMD chipset and NVIDIA drivers.
5. Install the SSD vendor utility and update the new drive's firmware.
6. Restore data from the verified backup.
7. Confirm the new SSD is first in UEFI boot order.
8. Keep the P3 disconnected until the new installation is stable.

A clean installation is safer than cloning because cloning forces a sustained
read of the failing source and can copy filesystem corruption. If cloning is
unavoidable, make a separate verified backup first and do not treat the clone as
the only copy.

## Isolation after replacement

- **Stable on NVMe:** the fault was within the old SATA path. Retire the P3-512
  regardless; its read/reallocation telemetry is not suitable for trusted use.
- **Event 129 returns only after reconnecting a known-good SATA SSD:** suspect
  cable, SATA port/controller, SATA power, or PSU.
- **NVMe errors or WHEA errors appear with the SATA drive disconnected:** expand
  investigation to the motherboard, PSU, RAM, BIOS, and PCIe subsystem.
- **No storage errors for two weeks of ordinary use:** confidence strongly
  favors the old SSD/SATA path as the root cause.

Do not use a benchmark as the acceptance test. Ordinary boot, updates, software
installation, development work, and event-log observation are safer and more
representative.

## Separate performance observation

The machine has one 16 GB DDR4-2667 DIMM, so memory operates single-channel.
That can reduce general responsiveness and game performance but cannot explain
Disk 0 retries, `storahci` resets, or storage bugchecks. Address memory only
after storage is stable.

## Historical records

The [documentation history index](history/README.md) preserves the original
2026-07-24 assessment and session handoff with prominent superseding notices.
