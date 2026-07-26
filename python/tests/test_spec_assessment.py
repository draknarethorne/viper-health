"""Tests for the advisory machine-capability assessment."""

from viper_health.analyzers.spec_assessment import (
    _cpu_generation,
    assess_system_capability,
)


def _solid_desktop() -> dict:
    return {
        "available": True,
        "ComputerSystem": {
            "Manufacturer": "ACME",
            "Model": "TowerPro",
            "TotalPhysicalMemoryBytes": 32 * 1024**3,
        },
        "OperatingSystem": {
            "Caption": "Microsoft Windows 11 Pro",
            "BuildNumber": "26100",
            "TotalVisibleMemoryKb": 32 * 1024**2,
            "FreePhysicalMemoryKb": 16 * 1024**2,
        },
        "Bios": {"ReleaseDateUtc": "2024-01-01T00:00:00Z"},
        "Cpu": [{"Name": "AMD Ryzen 7 5800X", "Cores": 8, "LogicalProcessors": 16, "LoadPercent": 10}],
        "MemoryModules": [
            {"CapacityBytes": 16 * 1024**3, "ConfiguredSpeedMhz": 3200},
            {"CapacityBytes": 16 * 1024**3, "ConfiguredSpeedMhz": 3200},
        ],
        "Gpus": [{"Name": "NVIDIA GeForce RTX 4070", "DriverDate": "2025-06-01T00:00:00Z"}],
        "SecureBootEnabled": True,
        "Tpm": {"Present": True},
        "Batteries": [],
    }


def _weak_old_laptop() -> dict:
    return {
        "available": True,
        "ComputerSystem": {
            "Manufacturer": "OldCo",
            "Model": "Netbook",
            "TotalPhysicalMemoryBytes": 4 * 1024**3,
        },
        "OperatingSystem": {
            "Caption": "Microsoft Windows 10 Home",
            "BuildNumber": "19045",
            "TotalVisibleMemoryKb": 4 * 1024**2,
            "FreePhysicalMemoryKb": 200 * 1024,  # very low free
        },
        "Bios": {"ReleaseDateUtc": "2016-05-01T00:00:00Z"},
        "Cpu": [{"Name": "Intel(R) Core(TM) i3-6100U CPU @ 2.30GHz", "Cores": 2, "LogicalProcessors": 4}],
        "MemoryModules": [{"CapacityBytes": 4 * 1024**3, "ConfiguredSpeedMhz": 1600}],
        "Gpus": [{"Name": "Intel(R) HD Graphics 520"}],
        "SecureBootEnabled": False,
        "Tpm": {"Present": False},
        "Batteries": [{"Name": "Battery", "EstimatedChargeRemaining": 80}],
    }


def test_cpu_generation_parses_intel_and_ryzen():
    assert _cpu_generation("Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz") == ("Intel Core i7", 8)
    assert _cpu_generation("Intel(R) Core(TM) i9-13900K") == ("Intel Core i9", 13)
    assert _cpu_generation("AMD Ryzen 7 5800X") == ("AMD Ryzen 7", 5)
    assert _cpu_generation("Some Unknown CPU") == ("Unknown", None)


def test_solid_desktop_rated_solid():
    result = assess_system_capability(_solid_desktop())

    assert result["available"] is True
    assert result["tier"] == "solid"
    assert result["is_laptop"] is False
    assert result["components"]["cpu"]["tier"] == "solid"
    assert result["components"]["memory"]["tier"] == "solid"
    assert result["components"]["gpu"]["tier"] == "solid"


def test_weak_old_laptop_rated_low_with_recommendations():
    result = assess_system_capability(_weak_old_laptop())

    assert result["tier"] in ("weak", "dated")
    assert result["is_laptop"] is True
    # Advisory recommendations should surface actionable optimizations.
    joined = " ".join(result["recommendations"]).lower()
    assert "windows 11" in joined or "windows 10" in joined
    assert "secure boot" in joined
    # Low free memory should be flagged.
    assert any("ram free" in note.lower() for note in result["components"]["memory"]["notes"])


def test_single_channel_memory_recommends_second_module():
    inventory = _solid_desktop()
    inventory["MemoryModules"] = [{"CapacityBytes": 32 * 1024**3, "ConfiguredSpeedMhz": 3200}]

    result = assess_system_capability(inventory)

    assert result["components"]["memory"]["detail"]["dual_channel"] is False
    assert any("dual-channel" in note.lower() for note in result["components"]["memory"]["notes"])


def test_integrated_only_gpu_is_dated():
    inventory = _solid_desktop()
    inventory["Gpus"] = [{"Name": "Intel(R) UHD Graphics 620"}]

    result = assess_system_capability(inventory)

    assert result["components"]["gpu"]["tier"] == "dated"
    assert result["components"]["gpu"]["detail"]["discrete_present"] is False


def test_unavailable_inventory_is_unknown_and_does_not_raise():
    result = assess_system_capability({"available": False, "error": "no admin"})

    assert result["available"] is False
    assert result["tier"] == "unknown"
    assert result["recommendations"]  # guidance to re-run elevated


def test_older_intel_generation_pulls_tier_down():
    inventory = _solid_desktop()
    # 8 cores but a 4th-gen part → age nudge applies.
    inventory["Cpu"] = [{"Name": "Intel(R) Core(TM) i7-4790K", "Cores": 4, "LogicalProcessors": 8}]

    result = assess_system_capability(inventory)

    notes = " ".join(result["components"]["cpu"]["notes"]).lower()
    assert "dated" in notes
