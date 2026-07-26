"""Advisory capability assessment from passive system specifications.

This analyzer turns collected hardware/OS facts (see
``collectors.system_inventory``) into a **capability tier** and concrete
optimization recommendations. It is deliberately kept separate from the
fault-evidence severity produced by ``analyzers.system_events`` and the
storage checks: a capable machine must never visually soften a real fault, and
a weak machine is not itself a "fault". Callers should render this as advisory
context, not fold it into GOOD/WARNING/CRITICAL health.

All functions are pure and deterministic. Missing facts degrade to ``unknown``
components rather than raising.
"""

from __future__ import annotations

import re
from typing import Any

# Tier vocabulary, strongest to weakest. Numeric scores drive aggregation only.
_TIER_SCORE = {"solid": 3, "capable": 2, "dated": 1, "weak": 0, "unknown": None}
_SCORE_TIER = {3: "solid", 2: "capable", 1: "dated", 0: "weak"}

_GIB = 1024 ** 3

# Integrated / non-discrete GPU signatures.
_INTEGRATED_GPU_HINTS = (
    "intel", "uhd", "hd graphics", "iris", "radeon graphics", "vega",
    "microsoft basic", "amd radeon(tm) graphics",
)


def _as_list(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _tier_from_score(score: float) -> str:
    if score >= 2.5:
        return "solid"
    if score >= 1.5:
        return "capable"
    if score >= 0.75:
        return "dated"
    return "weak"


def _cpu_generation(name: str) -> tuple[str, int | None]:
    """Best-effort family + generation parse for common desktop/laptop CPUs.

    Returns (family_label, generation) where generation is an int when it can be
    inferred (Intel Core iX-#### / AMD Ryzen ####), else None.
    """
    text = name or ""
    intel = re.search(r"\bi([3579])[\- ]?(\d{3,5})", text, re.IGNORECASE)
    if intel:
        digits = intel.group(2)
        # Intel gen is the leading 1-2 digits before the 3-digit SKU.
        gen = int(digits[:-3]) if len(digits) > 3 else int(digits[0])
        return f"Intel Core i{intel.group(1)}", gen
    ryzen = re.search(r"ryzen\s+([3579])\s+(\d{3,4})", text, re.IGNORECASE)
    if ryzen:
        series = ryzen.group(2)
        gen = int(series[0])
        return f"AMD Ryzen {ryzen.group(1)}", gen
    return "Unknown", None


def _assess_cpu(cpus: list[dict]) -> dict:
    if not cpus:
        return {"tier": "unknown", "notes": ["No CPU data was collected."]}
    cpu = cpus[0]
    name = str(cpu.get("Name") or "").strip()
    cores = cpu.get("Cores")
    threads = cpu.get("LogicalProcessors")
    load = cpu.get("LoadPercent")
    family, generation = _cpu_generation(name)

    notes: list[str] = []
    # Base tier from core/thread count.
    if isinstance(cores, int) and cores >= 8 or (isinstance(threads, int) and threads >= 16):
        score = 3
    elif isinstance(cores, int) and cores >= 6 or (isinstance(threads, int) and threads >= 12):
        score = 2
    elif isinstance(cores, int) and cores >= 4 or (isinstance(threads, int) and threads >= 8):
        score = 2
    elif isinstance(cores, int) and cores >= 2:
        score = 1
    elif cores is None and threads is None:
        return {"tier": "unknown", "notes": ["CPU core/thread counts were unavailable."], "detail": {"name": name}}
    else:
        score = 0

    # Age nudge: very old generations pull the tier down one step.
    if generation is not None:
        if (family.startswith("Intel") and generation <= 6) or (
            family.startswith("AMD Ryzen") and generation <= 1
        ):
            score = max(0, score - 1)
            notes.append(
                f"{family} generation {generation} is dated; expect weaker single-thread and efficiency."
            )
        elif (family.startswith("Intel") and generation <= 8) or (
            family.startswith("AMD Ryzen") and generation <= 2
        ):
            notes.append(
                f"{family} generation {generation} is serviceable but a few generations behind current."
            )

    if isinstance(load, (int, float)) and load >= 85:
        notes.append(f"CPU load was {load}% at collection; sustained high load can indicate background churn.")

    return {
        "tier": _SCORE_TIER[score],
        "notes": notes,
        "detail": {
            "name": name,
            "cores": cores,
            "threads": threads,
            "family": family,
            "generation": generation,
            "load_percent": load,
        },
    }


def _assess_memory(system: dict, os_info: dict, modules: list[dict]) -> dict:
    total_bytes = system.get("TotalPhysicalMemoryBytes")
    total_gib = (int(total_bytes) / _GIB) if isinstance(total_bytes, (int, float)) else None
    populated = len(modules)
    notes: list[str] = []

    if total_gib is None:
        return {"tier": "unknown", "notes": ["Installed memory size was unavailable."]}

    if total_gib >= 31:
        score = 3
    elif total_gib >= 15:
        score = 2
    elif total_gib >= 7:
        score = 1
    else:
        score = 0
        notes.append("Under 8 GiB installed; modern Windows multitasking will page heavily.")

    if populated == 1:
        notes.append(
            "Only one memory module is populated; adding a matched module enables dual-channel bandwidth."
        )

    # Live memory pressure from the OS snapshot (advisory only).
    free_kb = os_info.get("FreePhysicalMemoryKb")
    visible_kb = os_info.get("TotalVisibleMemoryKb")
    if isinstance(free_kb, (int, float)) and isinstance(visible_kb, (int, float)) and visible_kb:
        free_ratio = free_kb / visible_kb
        if free_ratio < 0.08:
            notes.append(
                f"Only {free_ratio * 100:.0f}% RAM free at collection; close heavy apps or add memory if this is typical."
            )

    speeds = [m.get("ConfiguredSpeedMhz") or m.get("SpeedMhz") for m in modules]
    speeds = [int(s) for s in speeds if isinstance(s, (int, float))]
    detail = {
        "total_gib": round(total_gib, 2),
        "modules_populated": populated,
        "configured_speed_mhz": max(speeds) if speeds else None,
        "dual_channel": populated >= 2,
    }
    return {"tier": _SCORE_TIER[score], "notes": notes, "detail": detail}


def _is_discrete(name: str) -> bool:
    lowered = name.casefold()
    if not lowered:
        return False
    return not any(hint in lowered for hint in _INTEGRATED_GPU_HINTS)


def _assess_gpu(gpus: list[dict]) -> dict:
    if not gpus:
        return {"tier": "unknown", "notes": ["No GPU data was collected."]}
    names = [str(g.get("Name") or "") for g in gpus]
    discrete = [g for g, n in zip(gpus, names) if _is_discrete(n)]
    notes: list[str] = []

    if discrete:
        score = 3
        chosen = discrete[0]
    else:
        score = 1
        chosen = gpus[0]
        notes.append("Only integrated graphics detected; fine for general use, limited for 3D/GPU workloads.")

    name = str(chosen.get("Name") or "")
    if "microsoft basic" in name.casefold():
        score = 0
        notes.append("Microsoft Basic Display Adapter active — the vendor GPU driver is not installed.")

    driver_date = chosen.get("DriverDate")
    if isinstance(driver_date, str) and len(driver_date) >= 4:
        year = _leading_year(driver_date)
        if year is not None and year <= 2022:
            notes.append(f"GPU driver dates to {year}; check the vendor site for a newer driver.")

    return {
        "tier": _SCORE_TIER[score],
        "notes": notes,
        "detail": {
            "primary": name,
            "discrete_present": bool(discrete),
            "adapter_count": len(gpus),
        },
    }


def _leading_year(iso_date: str) -> int | None:
    match = re.match(r"(\d{4})", iso_date)
    return int(match.group(1)) if match else None


def _assess_os_and_firmware(
    os_info: dict, bios: dict, secure_boot: Any, tpm: dict | None
) -> tuple[dict, list[str]]:
    notes: list[str] = []
    recommendations: list[str] = []
    caption = str(os_info.get("Caption") or "")
    build = os_info.get("BuildNumber")
    try:
        build_num = int(build)
    except (TypeError, ValueError):
        build_num = None

    if "windows 11" in caption.casefold() or (build_num is not None and build_num >= 22000):
        os_tier = "solid"
    elif "windows 10" in caption.casefold():
        os_tier = "dated"
        recommendations.append(
            "Windows 10 is past mainstream support; plan a Windows 11 upgrade or ESU on eligible hardware."
        )
    elif caption:
        os_tier = "weak"
        recommendations.append(f"{caption} is unsupported; upgrade to a supported Windows release.")
    else:
        os_tier = "unknown"

    if secure_boot is False:
        recommendations.append("Secure Boot is disabled; enable it in UEFI for firmware-level boot integrity.")
    if isinstance(tpm, dict) and tpm.get("Present") is False:
        notes.append("No TPM detected; required for some security features and Windows 11 upgrades.")

    bios_date = bios.get("ReleaseDateUtc")
    if isinstance(bios_date, str):
        year = _leading_year(bios_date)
        if year is not None and year <= 2021:
            recommendations.append(
                f"BIOS/UEFI dates to {year}; check the vendor for firmware updates (stability, security, NVMe fixes)."
            )

    detail = {
        "os": caption,
        "build": build,
        "secure_boot": secure_boot,
        "tpm_present": tpm.get("Present") if isinstance(tpm, dict) else None,
        "bios_release": bios_date,
    }
    return {"tier": os_tier, "notes": notes, "detail": detail}, recommendations


def assess_system_capability(inventory: dict[str, Any]) -> dict[str, Any]:
    """Assess machine capability from a system-inventory dict (advisory).

    Args:
        inventory: The ``SystemInventory.to_dict()`` payload.

    Returns:
        A JSON-serializable capability report with an overall ``tier``, per
        component assessments, and optimization ``recommendations``. Never
        raises; unavailable inventory yields ``tier == "unknown"``.
    """
    if not isinstance(inventory, dict) or inventory.get("available") is False:
        return {
            "available": False,
            "tier": "unknown",
            "summary": "System inventory was unavailable; capability could not be assessed.",
            "components": {},
            "recommendations": [
                "Re-run from an elevated PowerShell terminal to collect machine specifications.",
            ],
        }

    system = inventory.get("ComputerSystem") or {}
    os_info = inventory.get("OperatingSystem") or {}
    bios = inventory.get("Bios") or {}
    tpm = inventory.get("Tpm")
    cpus = _as_list(inventory.get("Cpu"))
    modules = _as_list(inventory.get("MemoryModules"))
    gpus = _as_list(inventory.get("Gpus"))
    batteries = _as_list(inventory.get("Batteries"))

    cpu = _assess_cpu(cpus)
    memory = _assess_memory(system, os_info, modules)
    gpu = _assess_gpu(gpus)
    os_firmware, os_recommendations = _assess_os_and_firmware(
        os_info, bios, inventory.get("SecureBootEnabled"), tpm if isinstance(tpm, dict) else None
    )

    components = {"cpu": cpu, "memory": memory, "gpu": gpu, "os_firmware": os_firmware}

    is_laptop = bool(batteries)
    if is_laptop:
        components["form_factor"] = {
            "tier": "capable",
            "notes": ["Battery present — this is a laptop; thermal and power limits cap sustained performance."],
            "detail": {"batteries": len(batteries)},
        }

    # Aggregate hardware tier from CPU/memory/GPU (OS/firmware inform advice,
    # not the hardware capability tier). Weight CPU and memory most.
    weights = {"cpu": 0.4, "memory": 0.4, "gpu": 0.2}
    weighted_sum = 0.0
    weight_total = 0.0
    for key, weight in weights.items():
        score = _TIER_SCORE.get(components[key]["tier"])
        if score is not None:
            weighted_sum += score * weight
            weight_total += weight

    if weight_total == 0:
        overall_tier = "unknown"
    else:
        overall_tier = _tier_from_score(weighted_sum / weight_total)

    # Collect recommendations from component notes + OS/firmware advice.
    recommendations: list[str] = []
    recommendations.extend(os_recommendations)
    for key in ("cpu", "memory", "gpu"):
        for note in components[key].get("notes", []):
            # Only surface actionable notes (those suggesting a change).
            if any(word in note.lower() for word in ("add", "close", "check", "update", "install", "enable")):
                recommendations.append(note)

    model = f"{str(system.get('Manufacturer') or '').strip()} {str(system.get('Model') or '').strip()}".strip()
    tier_labels = {
        "solid": "a solid, well-provisioned machine",
        "capable": "a capable machine for mainstream workloads",
        "dated": "a dated machine that still functions but is showing its age",
        "weak": "an underpowered machine for modern workloads",
        "unknown": "a machine whose capability could not be fully assessed",
    }
    form = "laptop" if is_laptop else "system"
    summary = (
        f"{model or 'This ' + form} is {tier_labels[overall_tier]} "
        f"(CPU: {cpu['tier']}, memory: {memory['tier']}, GPU: {gpu['tier']})."
    )

    if not recommendations:
        recommendations.append("No specification-level optimizations identified; hardware is well matched to modern use.")

    return {
        "available": True,
        "tier": overall_tier,
        "summary": summary,
        "is_laptop": is_laptop,
        "components": components,
        "recommendations": recommendations,
    }
