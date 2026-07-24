# Quick Reference: Running with Admin Privileges

## Option 1: Restart VS Code as Administrator (Recommended)

1. Close VS Code
2. Right-click VS Code icon → **"Run as administrator"**
3. Open your viper-health workspace
4. All terminals now have admin privileges
5. Run MFT scan:
   ```bash
   python -m viper_health.cli.scan_mft --drive C:
   ```

## Option 2: Elevated PowerShell from VS Code

In your current VS Code terminal:

```powershell
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "cd '$PWD'"
```

This opens a new admin PowerShell window. Then:

```powershell
cd C:\Viper-Health
.venv\Scripts\python.exe -m viper_health.cli.scan_mft --drive C:
```

## Option 3: Windows Terminal as Admin

1. Win + X → "Windows Terminal (Admin)"
2. Navigate to project:
   ```powershell
   cd C:\Viper-Health
   ```
3. Activate virtual environment:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
4. Run commands with admin privileges

---

## Essential Commands Requiring Admin

### MFT Health Scan
```bash
python -m viper_health.cli.scan_mft --drive C:
```

### TRIM Status Check
```powershell
fsutil behavior query DisableDeleteNotify
# Should show: DisableDeleteNotify = 0 (TRIM enabled)
```

### MFT Defragmentation
```powershell
defrag C: /U /V
# Run after cleanup, may take 10-30 minutes
```

### Enable TRIM (if disabled)
```powershell
fsutil behavior set DisableDeleteNotify 0
```

---

## Post-Cleanup Workflow

After cleaning up files today:

```bash
# 1. Run MFT scan (admin required)
python -m viper_health.cli.scan_mft --drive C: --output data/mft/post_cleanup.json

# 2. Check TRIM status (admin required)
fsutil behavior query DisableDeleteNotify

# 3. Let drive idle 60 minutes (TRIM + garbage collection)
# No action needed - just don't stress the drive

# 4. Re-run I/O benchmark to see improvement
python -m viper_health.cli.benchmark_io --output data/benchmarks/post_calm.json

# 5. Compare to previous benchmark
# Look for sequential write improvement
```

---

## What Each Tool Will Tell You

### Benchmark CLI (`benchmark_io`)
- ✅ **GOOD**: Performance healthy, no action needed
- ⚠️ **WARNING**: Moderate degradation, monitor and clean regularly
- ❌ **CRITICAL**: Severe performance issues, immediate action needed

**With enhanced recommendations, it will tell you:**
- Why performance is degraded (SLC cache, metadata pressure, thermal)
- Exact commands to run for diagnosis
- What to clean up first
- How to verify TRIM is working
- When to defragment MFT

### MFT Scan CLI (`scan_mft`)
- Reports MFT size (>2.5 GB = CRITICAL)
- Reports fragmentation (>10 fragments = CRITICAL)
- Total files and folders

**With enhanced recommendations, it will tell you:**
- Target cleanup areas (browser cache, VS Code, package managers)
- When and how to defragment MFT
- How to verify improvement after cleanup
- Related health checks to run

### Filesystem Scan (`suite --preset quick-check`)
- Identifies tiny-file hotspots (thousands of small files)
- Shows directory density problems
- Suppresses safe/expected paths

**Tells you:**
- Which directories to target for cleanup
- How many files in each hotspot
- Health score (0-100)

---

## "Calm Phase" Explained

### What is it?
After deleting files or heavy I/O, the drive needs time to recover:

1. **Windows sends TRIM** - Tells SSD which blocks are free
2. **SSD garbage collection** - Reorganizes data, reclaims space
3. **SLC cache recovery** - Cache reorganizes and recovers capacity

### How long?
- **Minimum**: 30 minutes
- **Recommended**: 60 minutes
- **After major cleanup**: 2-3 hours or overnight

### What qualifies as "idle"?
✅ Light web browsing, email, text editing  
❌ Gaming, video editing, large downloads, software compilation

### How to verify it helped?
```bash
# Before calm phase
python -m viper_health.cli.benchmark_io --output before_calm.json

# Wait 60 minutes...

# After calm phase
python -m viper_health.cli.benchmark_io --output after_calm.json

# Compare sequential write throughput
# Should improve if drive was stressed
```

---

## If Performance Stays Poor After Cleanup + Calm Phase

Run these checks (in order):

### 1. Check Free Space
```powershell
fsutil volume diskfree C:
```
**Need:** >20% free space for optimal performance

### 2. Verify TRIM is Enabled
```powershell
fsutil behavior query DisableDeleteNotify
```
**Expected:** DisableDeleteNotify = 0

### 3. Check Drive Temperature
Download CrystalDiskInfo (free)  
**Target:** <55°C optimal, <70°C acceptable

### 4. Scan SMART Data
Use CrystalDiskInfo or `smartctl -a`  
**Look for:** Reallocated sectors, pending sectors, errors

### 5. Check Background Processes
```powershell
resmon.exe  # Resource Monitor → Disk tab
```
**Look for:** Windows Search, antivirus, cloud sync hammering disk

### 6. Defragment MFT (if fragmented)
```powershell
defrag C: /U /V  # Requires admin, takes 10-30 min
```

### 7. Update Firmware
Check manufacturer's website for SSD firmware updates

---

## When to Run Each Tool

### Daily (or after cleanup)
```bash
python -m viper_health.cli.suite --preset user-data --console-summary
```

### Weekly
```bash
python -m viper_health.cli.benchmark_io --output data/benchmarks/week_$(date +%V).json
```

### Monthly  
```bash
python -m viper_health.cli.suite --preset full-system --output-dir reports/monthly/
python -m viper_health.cli.scan_mft --drive C: --output data/mft/monthly.json
```

### After Major Cleanup
```bash
# 1. Scan MFT
python -m viper_health.cli.scan_mft --drive C:

# 2. Wait 60 min (calm phase)

# 3. Re-run benchmark
python -m viper_health.cli.benchmark_io --output data/benchmarks/post_cleanup.json
```

---

## Quick Win Checklist

If your SSD is slow **right now**:

- [ ] Check free space (need >20%)
- [ ] Check TRIM enabled (`fsutil behavior query DisableDeleteNotify`)
- [ ] Open Resource Monitor, check what's hammering disk
- [ ] Run filesystem scan: `python -m viper_health.cli.suite --preset quick-check`
- [ ] Clean up identified hotspots
- [ ] Let drive idle 60 minutes
- [ ] Re-run benchmark to verify improvement

---

## Still Need Help?

See the comprehensive guide: [`docs/SSD-HEALTH-MONITORING-GUIDE.md`](./SSD-HEALTH-MONITORING-GUIDE.md)

Contains:
- What analyzers are missing from viper-health
- Deep troubleshooting workflows
- Understanding QLC SSD behavior
- Advanced diagnostics
