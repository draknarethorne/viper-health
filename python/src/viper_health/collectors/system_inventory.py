"""Passive Windows hardware, firmware, OS, and runtime inventory collector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from viper_health.utils.windows_powershell import run_powershell_json


@dataclass(frozen=True)
class SystemInventory:
    """Best-effort system specification snapshot."""

    available: bool
    collected_at_utc: str | None
    data: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "collected_at_utc": self.collected_at_utc,
            **self.data,
            "error": self.error,
        }


def collect_system_inventory() -> SystemInventory:
    """Collect stable specifications and lightweight runtime facts via CIM.

    Serial numbers, UUIDs, user names, and network addresses are deliberately
    excluded so reports are safer to transport through Git and share with AI.
    ACPI thermal-zone readings are included as raw firmware-reported facts and
    must not be treated as authoritative CPU/GPU temperatures.
    """
    script = r"""
$ErrorActionPreference = 'Stop'
try {
    $cs = Get-CimInstance Win32_ComputerSystem
    $os = Get-CimInstance Win32_OperatingSystem
    $board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
    $bios = Get-CimInstance Win32_BIOS | Select-Object -First 1
    $cpu = @(Get-CimInstance Win32_Processor | ForEach-Object {
        [PSCustomObject]@{
            Name = $_.Name
            Manufacturer = $_.Manufacturer
            Cores = $_.NumberOfCores
            LogicalProcessors = $_.NumberOfLogicalProcessors
            MaxClockMhz = $_.MaxClockSpeed
            CurrentClockMhz = $_.CurrentClockSpeed
            LoadPercent = $_.LoadPercentage
            Status = $_.Status
        }
    })
    $memory = @(Get-CimInstance Win32_PhysicalMemory | ForEach-Object {
        [PSCustomObject]@{
            Manufacturer = $_.Manufacturer
            PartNumber = ([string]$_.PartNumber).Trim()
            CapacityBytes = $_.Capacity
            SpeedMhz = $_.Speed
            ConfiguredSpeedMhz = $_.ConfiguredClockSpeed
            BankLabel = $_.BankLabel
            DeviceLocator = $_.DeviceLocator
        }
    })
    $gpu = @(Get-CimInstance Win32_VideoController | ForEach-Object {
        [PSCustomObject]@{
            Name = $_.Name
            DriverVersion = $_.DriverVersion
            DriverDate = if ($_.DriverDate) { $_.DriverDate.ToUniversalTime().ToString('o') } else { $null }
            AdapterRamBytes = $_.AdapterRAM
            Status = $_.Status
            VideoMode = $_.VideoModeDescription
        }
    })
    $battery = @(Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | ForEach-Object {
        [PSCustomObject]@{
            Name = $_.Name
            Status = $_.Status
            EstimatedChargeRemaining = $_.EstimatedChargeRemaining
            BatteryStatus = $_.BatteryStatus
        }
    })
    $thermal = @(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | ForEach-Object {
        [PSCustomObject]@{
            InstanceName = $_.InstanceName
            CurrentTemperatureKelvinTenths = $_.CurrentTemperature
            CriticalTripPointKelvinTenths = $_.CriticalTripPoint
        }
    })
    $secureBoot = $null
    try { $secureBoot = Confirm-SecureBootUEFI -ErrorAction Stop } catch {}
    $tpm = $null
    try {
        $tpmRaw = Get-Tpm -ErrorAction Stop
        $tpm = [PSCustomObject]@{
            Present = $tpmRaw.TpmPresent
            Ready = $tpmRaw.TpmReady
            Enabled = $tpmRaw.TpmEnabled
            Activated = $tpmRaw.TpmActivated
            ManufacturerVersion = $tpmRaw.ManufacturerVersion
        }
    } catch {}
    [PSCustomObject]@{
        Available = $true
        CollectedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        ComputerSystem = [PSCustomObject]@{
            Manufacturer = $cs.Manufacturer
            Model = $cs.Model
            SystemType = $cs.SystemType
            TotalPhysicalMemoryBytes = $cs.TotalPhysicalMemory
        }
        OperatingSystem = [PSCustomObject]@{
            Caption = $os.Caption
            Version = $os.Version
            BuildNumber = $os.BuildNumber
            Architecture = $os.OSArchitecture
            InstallDateUtc = if ($os.InstallDate) { $os.InstallDate.ToUniversalTime().ToString('o') } else { $null }
            LastBootUtc = if ($os.LastBootUpTime) { $os.LastBootUpTime.ToUniversalTime().ToString('o') } else { $null }
            TotalVisibleMemoryKb = $os.TotalVisibleMemorySize
            FreePhysicalMemoryKb = $os.FreePhysicalMemory
        }
        Baseboard = [PSCustomObject]@{
            Manufacturer = $board.Manufacturer
            Product = $board.Product
            Version = $board.Version
        }
        Bios = [PSCustomObject]@{
            Manufacturer = $bios.Manufacturer
            Name = $bios.Name
            SMBIOSVersion = $bios.SMBIOSBIOSVersion
            ReleaseDateUtc = if ($bios.ReleaseDate) { $bios.ReleaseDate.ToUniversalTime().ToString('o') } else { $null }
        }
        Cpu = $cpu
        MemoryModules = $memory
        Gpus = $gpu
        Batteries = $battery
        AcpiThermalZones = $thermal
        SecureBootEnabled = $secureBoot
        Tpm = $tpm
        Error = $null
    } | ConvertTo-Json -Depth 7 -Compress
} catch {
    [PSCustomObject]@{
        Available = $false
        CollectedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        Error = $_.Exception.Message
    } | ConvertTo-Json -Depth 3 -Compress
}
"""
    result = run_powershell_json(script, timeout_seconds=120)
    if not result.available or not isinstance(result.data, dict):
        return SystemInventory(
            available=False,
            collected_at_utc=None,
            data={},
            error=result.error or "System inventory was unavailable",
        )

    payload = dict(result.data)
    available = bool(payload.pop("Available", True))
    collected_at = str(payload.pop("CollectedAtUtc", "") or "") or None
    error = str(payload.pop("Error", "") or "") or None
    return SystemInventory(
        available=available,
        collected_at_utc=collected_at,
        data=payload,
        error=error,
    )
