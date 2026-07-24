# SSD Health Monitoring Guide for DRAM-less QLC Drives

## Table of Contents
1. [What We Have](#what-we-have-current-toolkit)
2. [What We're Missing](#what-were-missing-critical-gaps)
3. [Recommended Monitoring Workflow](#recommended-monitoring-workflow)
4. [Understanding "Calm Phase"](#understanding-calm-phase)
5. [Troubleshooting Slow Performance](#troubleshooting-slow-performance)

---

## What We Have (Current Toolkit)

### ✅ Implemented Analyzers

| Tool | Purpose | Status |
|------|---------|--------|
| **I/O Benchmarks** | Measure seq/random read/write performance | ✅ Complete |
| **MFT Analysis** | Track MFT size and fragmentation | ✅ Complete |
| **Tiny-File Hotspots** | Identify metadata pressure from small files | ✅ Complete |
| **Directory Density** | Find directories with excessive file counts | ✅ Complete |
| **Health Scoring** | Weighted overall health assessment | ✅ Complete |
| **Suite Runner** | Preset-based multi-target scanning | ✅ Complete |

### Current Capabilities

- **Filesystem Pressure Detection:** Identify tiny-file proliferation and directory bloat
- **Performance Baseline:** Measure I/O throughput and IOPS
- **Metadata Health:** Track MFT size and fragmentation
- **Safety-First Design:** Read-only defaults, immutable path protection
- **Multi-Format Reports:** JSON, Markdown, console output with color coding

---

## What We're Missing (Critical Gaps)

### 🚨 High Priority (Essential for SSD Health)

#### 1. TRIM Status Monitoring
**Why It Matters:**
- TRIM tells the SSD which blocks are no longer in use
- Without TRIM, SSD can't reclaim deleted space efficiently
- Critical for DRAM-less QLC drives (no mapping cache)

**What to Build:**
```python
# python/src/viper_health/collectors/trim_status.py
def check_trim_status(drive: str = "C:") -> dict:
    """
    Check if TRIM is enabled for the drive.
    Uses: fsutil behavior query DisableDeleteNotify
    Returns: {enabled: bool, message: str}
    """
```

**CLI Command:**
```bash
python -m viper_health.cli.check_trim --drive C:
```

**Impact:** If TRIM is disabled, your SSD will continuously degrade even after cleanup.

---

#### 2. Free Space Monitoring
**Why It Matters:**
- SSDs need 15-20% free space for optimal performance
- QLC drives especially need headroom for wear leveling
- SLC cache size depends on available free space

**What to Build:**
```python
# python/src/viper_health/collectors/disk_space.py
def analyze_disk_space(drive: str = "C:") -> dict:
    """
    Track free space, warn when <20% free.
    Returns: {
        total_gb: float,
        used_gb: float,
        free_gb: float,
        free_percent: float,
        severity: "good"|"warning"|"critical"
    }
    """
```

**Thresholds:**
- `<10% free` = CRITICAL (immediate action needed)
- `10-20% free` = WARNING (clean up soon)
- `>20% free` = GOOD

---

#### 3. Drive Temperature Monitoring
**Why It Matters:**
- High temps (>70°C) trigger thermal throttling
- QLC NAND is more temperature-sensitive than TLC
- Sustained high temps reduce drive lifespan

**What to Build:**
```python
# python/src/viper_health/collectors/drive_temp.py
def get_drive_temperature(drive: str = "C:") -> dict:
    """
    Query SMART temperature data.
    Uses: wmic or smartctl (if available)
    Returns: {
        temperature_c: float,
        severity: "good"|"warning"|"critical"
    }
    """
```

**Thresholds:**
- `<55°C` = GOOD (optimal)
- `55-70°C` = WARNING (monitor)
- `>70°C` = CRITICAL (throttling likely)

---

#### 4. SMART Data Analysis
**Why It Matters:**
- SMART attributes reveal drive health (wear level, reallocated sectors, etc.)
- Power-on hours, write amplification, total bytes written
- Early warning of impending failure

**What to Build:**
```python
# python/src/viper_health/collectors/smart_data.py
def analyze_smart_data(drive: str = "C:") -> dict:
    """
    Parse SMART attributes.
    Requires: smartctl (smartmontools) or wmic
    Key attributes:
    - 05: Reallocated Sector Count
    - 09: Power-On Hours
    - 0C: Power Cycle Count
    - C2: Temperature
    - F1: Total LBAs Written
    """
```

**Use External Tool:** CrystalDiskInfo or `smartctl` from smartmontools

---

#### 5. Trend Tracking / Baseline Comparison
**Why It Matters:**
- Single-point measurements don't show degradation
- Need weekly/monthly baselines to track performance over time
- Identify gradual decline before it becomes critical

**What to Build:**
```python
# python/src/viper_health/analyzers/trend_analyzer.py
def compare_to_baseline(current_results: dict, baseline_path: Path) -> dict:
    """
    Compare current scan results to saved baseline.
    Detect:
    - Performance regression (benchmark throughput down >20%)
    - MFT size growth (>500 MB increase)
    - Tiny-file count explosion (>50K increase)
    Returns: {changes: [...], severity: str, alerts: [...]}
    """
```

**Workflow:**
1. Save baseline after cleanup: `--output data/baselines/week1.json`
2. Compare weekly: `python -m viper_health.cli.compare_baseline --baseline data/baselines/week1.json`

---

### ⚠️ Medium Priority (Useful for Deep Diagnostics)

#### 6. Background Process I/O Monitoring
**Why It Matters:**
- Rogue processes can hammer the drive (Windows Search, antivirus, cloud sync)
- Identify what's causing sustained high I/O

**Tools to Integrate:**
- Windows Resource Monitor → Disk tab
- Process Explorer (SysInternals)
- `Get-Process | Sort-Object -Property WorkingSet -Descending`

**What to Build:**
```python
# python/src/viper_health/collectors/io_processes.py
def identify_high_io_processes() -> list[dict]:
    """
    Query top I/O processes via WMI or psutil.
    Returns: [{name, pid, read_bytes, write_bytes}]
    """
```

---

#### 7. Write Amplification Tracking
**Why It Matters:**
- Ratio of NAND writes to host writes
- High write amplification = excessive garbage collection overhead
- Indicates fragmentation or small write patterns

**Data Source:**
- SMART attribute F1 (Total LBAs Written) / F2 (Total LBAs Read)
- Compare to filesystem write tracking

**Implementation:**
Integrate with SMART data collector (item #4 above)

---

#### 8. Indexing Service Detection
**Why It Matters:**
- Windows Search indexing hammers SSDs with tiny-file reads
- Can cause sustained 100% disk usage
- Should be disabled on high-churn folders

**What to Build:**
```python
# python/src/viper_health/analyzers/indexing_check.py
def check_indexing_status(path: Path) -> dict:
    """
    Check if Windows Search indexing is enabled for path.
    Returns: {indexed: bool, recommendation: str}
    """
```

**Recommendation Engine:**
- If tiny-file hotspot AND indexed → suggest disabling indexing
- Folders to consider: node_modules, .git, cache, temp

---

#### 9. Defragmentation Scheduler
**Why It Matters:**
- MFT defragmentation should be scheduled after cleanup
- SSDs don't need traditional defrag, but MFT defrag is valuable
- QLC benefits from occasional filesystem optimization

**What to Build:**
```powershell
# powershell/PSViperHealth/Maintenance/Invoke-MFTDefrag.ps1
function Invoke-MFTDefrag {
    param([string]$Drive = "C:")
    
    # Check if admin
    # Run defrag C: /U /V
    # Monitor progress
    # Re-check MFT fragmentation after
}
```

---

### 💡 Low Priority (Nice to Have)

#### 10. SSD Firmware Version Check
- Outdated firmware may have performance bugs
- Check manufacturer's site for updates

#### 11. Over-Provisioning Calculator
- Recommend over-provisioning space for QLC drives
- Improves endurance and performance

#### 12. Power Loss Protection Check
- Detect if drive has power-loss protection (PLP)
- DRAM-less drives often lack PLP

---

## Recommended Monitoring Workflow

### Daily/After Cleanup
```bash
# 1. Run filesystem scan
python -m viper_health.cli.suite --preset user-data --console-summary

# 2. Check for critical findings
# If warnings/criticals, clean up identified hotspots

# 3. Let drive idle 30-60 minutes (calm phase)
# Windows runs TRIM, SSD runs garbage collection
```

### Weekly
```bash
# 1. Run full I/O benchmark
python -m viper_health.cli.benchmark_io --output data/benchmarks/week$(date +%V).json

# 2. Compare to baseline
python -m viper_health.cli.compare_baseline --baseline data/baselines/baseline.json

# 3. Check MFT health (requires admin)
python -m viper_health.cli.scan_mft --drive C: --output data/mft/week$(date +%V).json

# 4. Review trends for degradation
```

### Monthly
```bash
# 1. Run full system scan
python -m viper_health.cli.suite --preset full-system --output-dir reports/monthly/

# 2. Review SMART data
# Use CrystalDiskInfo or smartctl -a /dev/sdX

# 3. Check drive temperature trends
# Use HWiNFO64 sensor log

# 4. Plan cleanup based on findings
```

### After Major Cleanup
```bash
# 1. Save new baseline
python -m viper_health.cli.benchmark_io --output data/baselines/post_cleanup_$(date +%Y%m%d).json

# 2. Wait 60 minutes for calm phase

# 3. Re-run benchmark to see improvement
python -m viper_health.cli.benchmark_io

# 4. Compare before/after
```

---

## Understanding "Calm Phase"

### What Happens During Calm Phase?

**Windows Side (TRIM):**
1. OS sends TRIM commands for deleted blocks
2. File system updates MFT to reflect deletions
3. Prefetch cache clears and rebuilds

**SSD Side (Garbage Collection):**
1. Controller marks TRIM'd blocks as free
2. Garbage collection consolidates valid data
3. SLC cache reorganizes and recovers capacity
4. Wear leveling redistributes writes

### How Long to Wait?
- **Minimum:** 30 minutes of idle time
- **Recommended:** 60 minutes
- **Heavy cleanup:** 2-3 hours or overnight

### What is "Idle"?
- No active file operations (copying, installing, etc.)
- Light browsing/email is fine
- Avoid: video editing, gaming, large downloads, software compilation

### How to Verify Calm Phase Completed?
```bash
# Before calm phase
python -m viper_health.cli.benchmark_io --output before_calm.json

# Wait 60 minutes (idle)

# After calm phase
python -m viper_health.cli.benchmark_io --output after_calm.json

# Compare throughput - should see improvement if drive was stressed
```

---

## Troubleshooting Slow Performance

### If Sequential Write <100 MB/s (CRITICAL)

**Step 1: Check Free Space**
```powershell
Get-PSDrive C | Select-Object Used,Free
```
- Ensure >20% free space
- If <15%, this is your primary problem

**Step 2: Check Background Processes**
```powershell
# Open Resource Monitor
resmon.exe
# Go to Disk tab, sort by Total (B/sec)
```
- Look for sustained high I/O (Windows Search, antivirus, cloud sync)
- Temporarily disable/pause to test

**Step 3: Check TRIM Status**
```powershell
fsutil behavior query DisableDeleteNotify
```
- Should show: `DisableDeleteNotify = 0` (TRIM enabled)
- If disabled: `fsutil behavior set DisableDeleteNotify 0`

**Step 4: Check Drive Temperature**
- Download CrystalDiskInfo or HWiNFO64
- If >70°C, improve cooling or reduce workload

**Step 5: Scan for Tiny-File Hotspots**
```bash
python -m viper_health.cli.suite --preset full-system --console-summary
```
- Clean up identified hotspots (browser cache, temp, etc.)

**Step 6: Check MFT Health**
```bash
python -m viper_health.cli.scan_mft --drive C:
```
- If fragmented, run: `defrag C: /U /V` (requires admin)

**Step 7: Allow Calm Phase**
- Let system idle for 60+ minutes
- Re-run benchmark to see if performance recovers

---

### If Performance Doesn't Recover

**Hardware Issues:**
1. **Failing Drive:** Check SMART data for reallocated sectors, errors
2. **Thermal Throttling:** Improve case airflow, add heatsink
3. **Power Delivery:** Ensure adequate PSU, check power cables
4. **Interface Issues:** Re-seat M.2/SATA connection, test different port

**Software Issues:**
1. **Driver Problems:** Update chipset/storage drivers
2. **Firmware Outdated:** Check manufacturer for firmware updates
3. **Write Caching Disabled:** Ensure write caching enabled in Device Manager
4. **AHCI Mode:** Ensure SATA mode is AHCI (not IDE) in BIOS

**Configuration Issues:**
1. **Insufficient Over-Provisioning:** Consider leaving 10-15% unpartitioned
2. **4K Alignment:** Check partition alignment (should be 2048 sectors)
3. **TRIM Disabled:** Verify TRIM is working
4. **Page File on SSD:** Move page file to secondary drive if low space

---

## Next Steps for This Project

### Priority 1: Build Missing Core Analyzers
1. TRIM status checker
2. Free space monitor with thresholds
3. Baseline comparison / trend tracking

### Priority 2: Enhanced Reporting
1. Add trend graphs (if matplotlib available)
2. Combined health report (all metrics in one view)
3. Actionable recommendations based on findings

### Priority 3: Automation
1. Scheduled health checks (Task Scheduler integration)
2. Email/notification alerts for critical findings
3. Auto-cleanup dry-run generator

### Priority 4: PowerShell Parity
1. Port Python analyzers to PowerShell module
2. Windows-native tooling for sysadmins
3. Integration with Windows Admin Center

---

## Quick Reference Commands

### Essential Health Checks (Run These First)
```bash
# Free space
fsutil volume diskfree C:

# TRIM status (0 = enabled, 1 = disabled)
fsutil behavior query DisableDeleteNotify

# Drive info
wmic diskdrive get model,size,status

# MFT info (requires admin)
fsutil fsinfo ntfsinfo C:
```

### If Drive is Slow Right Now
```powershell
# 1. Check what's using the disk
resmon.exe  # Resource Monitor → Disk tab

# 2. Check free space
Get-PSDrive C | Select-Object Used,Free,@{Name="Free%";Expression={[math]::Round($_.Free/$($_.Used+$_.Free)*100,1)}}

# 3. Run quick viper-health check
python -m viper_health.cli.suite --preset quick-check --console-summary
```

### After Cleanup
```bash
# 1. Let drive calm down (wait 60 min)
# 2. Re-run benchmark
python -m viper_health.cli.benchmark_io

# 3. Check MFT (admin required)
python -m viper_health.cli.scan_mft --drive C:

# 4. Defrag MFT if fragmented (admin required)
defrag C: /U /V
```

---

## Conclusion

Your viper-health toolkit provides excellent **filesystem pressure detection**, but needs additional **hardware health monitoring** to get the complete picture of SSD health.

**Critical Missing Pieces:**
1. ✅ TRIM status verification
2. ✅ Free space thresholds
3. ✅ Trend/baseline tracking
4. ⚠️ Temperature monitoring (use external tools for now)
5. ⚠️ SMART data analysis (use CrystalDiskInfo for now)

**Immediate Action Items:**
1. Run elevated prompt for MFT scan
2. Check TRIM status: `fsutil behavior query DisableDeleteNotify`
3. Verify >20% free space: `fsutil volume diskfree C:`
4. Save current benchmark as baseline
5. Install CrystalDiskInfo for SMART/temp monitoring

After your cleanup today, **wait 60 minutes**, then re-run benchmarks to measure improvement.
