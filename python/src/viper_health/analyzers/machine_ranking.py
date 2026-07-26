"""Rank machines by performance and configuration (advisory).

Combines three signals into a single 0-100 *performance & configuration* score
used only for ordering machines relative to each other:

- **capability** — hardware specs tier (from ``spec_assessment``)
- **configuration** — filesystem/storage hygiene (free space, tiny-file ratio,
  TRIM, MFT)
- **performance** — measured I/O benchmark medians, when available

Fault severity is a **gate**, not a component: a machine with WARNING or
CRITICAL fault evidence is capped so it can never rank at the top on specs
alone. The score is explicitly a relative ranking aid, not a health verdict —
health remains the evidence-based GOOD/WARNING/CRITICAL severity.

All functions are pure and deterministic.
"""

from __future__ import annotations

from typing import Any

_CAPABILITY_SCORE = {
    "SOLID": 100.0,
    "CAPABLE": 75.0,
    "DATED": 45.0,
    "WEAK": 20.0,
    "UNKNOWN": None,
}

# Per-test throughput (MB/s) bands → subscore. Mirrors benchmark severity tiers.
_BENCH_BANDS = {
    "sequential_write": (200.0, 100.0),
    "sequential_read": (800.0, 400.0),
    "random_write": (50.0, 20.0),
    "random_read": (300.0, 100.0),
}

# Fault severity caps: a machine cannot score above the cap for its severity.
_FAULT_CAP = {"critical": 25.0, "warning": 60.0}

_COMPONENT_WEIGHTS = {"capability": 0.4, "configuration": 0.35, "performance": 0.25}

# Storage class inference and per-class expected throughput (MB/s). Expected
# values are class ceilings; the spec-vs-actual layer reports how close a drive
# comes to its class, which surfaces degradation or entry-tier hardware.
_STORAGE_CLASS_SPEC = {"nvme": 100.0, "sata": 70.0, "usb": 45.0, "hdd": 30.0, "other": 50.0}

_STORAGE_EXPECTED = {
    "nvme": {"sequential_write": 1000.0, "sequential_read": 2000.0, "random_write": 100.0, "random_read": 300.0},
    "sata": {"sequential_write": 400.0, "sequential_read": 500.0, "random_write": 60.0, "random_read": 200.0},
    "usb": {"sequential_write": 150.0, "sequential_read": 300.0, "random_write": 20.0, "random_read": 80.0},
    "hdd": {"sequential_write": 120.0, "sequential_read": 160.0, "random_write": 2.0, "random_read": 2.0},
    "other": {"sequential_write": 200.0, "sequential_read": 400.0, "random_write": 30.0, "random_read": 100.0},
}


def storage_class(row: dict[str, Any]) -> str:
    """Infer a coarse storage class from bus and media type."""
    bus = str(row.get("bus", "")).lower()
    media = str(row.get("media_type", "")).lower()
    if "nvme" in bus:
        return "nvme"
    if "usb" in bus:
        return "usb"
    if "sata" in bus or "ata" in bus:
        return "sata" if "ssd" in media else "hdd"
    if "raid" in bus or "vmd" in bus:
        # RAID/VMD commonly front NVMe SSDs on desktops/laptops.
        return "nvme" if "ssd" in media or media == "" else "other"
    if "ssd" in media:
        return "sata"
    if "hdd" in media or media in {"unspecified", "hard disk"}:
        return "hdd"
    return "other"


def resource_spec_scores(row: dict[str, Any]) -> dict[str, float | None]:
    """Per-resource *spec* subscores (0-100) from capability tiers + drive class."""
    components = row.get("capability_components") or {}

    def _tier_score(name: str) -> float | None:
        comp = components.get(name)
        tier = comp.get("tier") if isinstance(comp, dict) else comp
        if not tier:
            return None
        return _CAPABILITY_SCORE.get(str(tier).upper())

    storage = _STORAGE_CLASS_SPEC.get(storage_class(row)) if row.get("drive") else None
    return {
        "cpu": _tier_score("cpu"),
        "memory": _tier_score("memory"),
        "gpu": _tier_score("gpu"),
        "storage": storage,
    }


def _efficiency_verdict(efficiency: float) -> str:
    if efficiency >= 0.9:
        return "meets"
    if efficiency >= 0.6:
        return "below"
    return "well below"


def storage_expected_vs_actual(row: dict[str, Any]) -> dict[str, Any]:
    """Compare measured storage throughput to its class expectation.

    Returns per-test expected/actual/efficiency plus an overall verdict. When no
    benchmark data is present, ``available`` is False and ``verdict`` is
    ``not measured`` — spec facts alone cannot prove actual performance.
    """
    cls = storage_class(row)
    expected = _STORAGE_EXPECTED.get(cls, _STORAGE_EXPECTED["other"])
    benchmarks = row.get("benchmarks") or {}

    tests: list[dict[str, Any]] = []
    efficiencies: list[float] = []
    for test_name, expected_value in expected.items():
        actual = benchmarks.get(test_name)
        if not isinstance(actual, (int, float)) or expected_value <= 0:
            continue
        efficiency = round(actual / expected_value, 2)
        efficiencies.append(efficiency)
        tests.append(
            {
                "test": test_name,
                "expected_mb_s": expected_value,
                "actual_mb_s": round(float(actual), 1),
                "efficiency": efficiency,
                "verdict": _efficiency_verdict(efficiency),
            }
        )

    if not tests:
        return {"available": False, "storage_class": cls, "tests": [], "verdict": "not measured"}

    mean_efficiency = round(sum(efficiencies) / len(efficiencies), 2)
    return {
        "available": True,
        "storage_class": cls,
        "tests": tests,
        "mean_efficiency": mean_efficiency,
        "verdict": _efficiency_verdict(mean_efficiency),
    }


def capability_subscore(capability_tier: str | None) -> float | None:
    """Map a capability tier label to a 0-100 subscore."""
    if not capability_tier:
        return None
    return _CAPABILITY_SCORE.get(str(capability_tier).upper())


def configuration_subscore(row: dict[str, Any]) -> float | None:
    """Score storage/filesystem hygiene from available configuration signals."""
    score = 100.0
    signals = 0

    free = row.get("free_percent")
    if isinstance(free, (int, float)):
        signals += 1
        if free < 10:
            score -= 35
        elif free < 20:
            score -= 15

    tiny = row.get("tiny_file_ratio")
    if isinstance(tiny, (int, float)):
        signals += 1
        if tiny >= 50:
            score -= 30
        elif tiny >= 25:
            score -= 20
        elif tiny >= 10:
            score -= 10

    trim = row.get("trim_enabled")
    if trim is not None:
        signals += 1
        if trim is False:
            score -= 20

    mft = row.get("mft_severity")
    if mft:
        signals += 1
        if str(mft).lower() == "critical":
            score -= 25
        elif str(mft).lower() == "warning":
            score -= 10

    if signals == 0:
        return None
    return max(0.0, min(100.0, score))


def performance_subscore(benchmarks: dict[str, float] | None) -> float | None:
    """Average per-test throughput subscores from benchmark medians."""
    if not benchmarks:
        return None
    subscores: list[float] = []
    for test_name, (good, warn) in _BENCH_BANDS.items():
        value = benchmarks.get(test_name)
        if not isinstance(value, (int, float)):
            continue
        if value >= good:
            subscores.append(100.0)
        elif value >= warn:
            subscores.append(60.0)
        else:
            subscores.append(25.0)
    if not subscores:
        return None
    return sum(subscores) / len(subscores)


def score_machine(row: dict[str, Any]) -> dict[str, Any]:
    """Compute a machine's performance & configuration score with breakdown."""
    components = {
        "capability": capability_subscore(row.get("capability")),
        "configuration": configuration_subscore(row),
        "performance": performance_subscore(row.get("benchmarks")),
    }

    weighted_sum = 0.0
    weight_total = 0.0
    for name, weight in _COMPONENT_WEIGHTS.items():
        value = components[name]
        if value is not None:
            weighted_sum += value * weight
            weight_total += weight

    if weight_total == 0:
        raw_score: float | None = None
    else:
        raw_score = round(weighted_sum / weight_total, 1)

    severity = str(row.get("severity", "unknown")).lower()
    cap = _FAULT_CAP.get(severity)
    fault_limited = False
    if raw_score is None:
        score = None
    elif cap is not None and raw_score > cap:
        score = cap
        fault_limited = True
    else:
        score = raw_score

    return {
        "score": score,
        "raw_score": raw_score,
        "components": components,
        "fault_limited": fault_limited,
        "severity": severity,
    }


def _sort_key(entry: dict[str, Any]) -> tuple:
    score = entry["ranking"]["score"]
    # None scores sort last; higher scores rank first.
    has_score = 0 if score is None else 1
    return (has_score, score if score is not None else 0.0)


def rank_machines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return rows annotated with a ``ranking`` dict and 1-based ``rank``.

    Rows are returned sorted best-first. Machines with no scorable signals are
    placed last with ``rank`` still assigned for stable display.
    """
    annotated = [{**row, "ranking": score_machine(row)} for row in rows]
    annotated.sort(key=_sort_key, reverse=True)
    for index, entry in enumerate(annotated, start=1):
        entry["rank"] = index
    return annotated
