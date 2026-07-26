"""Tests for layered machine ranking (specs vs actual performance)."""

from viper_health.analyzers.machine_ranking import (
    configuration_subscore,
    performance_subscore,
    rank_machines,
    resource_spec_scores,
    score_machine,
    storage_class,
    storage_expected_vs_actual,
)


def _solid_row(**overrides):
    row = {
        "host": "DESK",
        "capability": "SOLID",
        "capability_components": {
            "cpu": {"tier": "solid"},
            "memory": {"tier": "solid"},
            "gpu": {"tier": "capable"},
        },
        "severity": "GOOD",
        "free_percent": 40.0,
        "tiny_file_ratio": 5.0,
        "trim_enabled": True,
        "mft_severity": "good",
        "bus": "NVMe",
        "media_type": "SSD",
        "drive": "Fast NVMe",
        "benchmarks": {
            "sequential_write": 1500.0,
            "sequential_read": 3000.0,
            "random_write": 120.0,
            "random_read": 400.0,
        },
    }
    row.update(overrides)
    return row


def test_configuration_subscore_penalizes_poor_hygiene():
    good = configuration_subscore(_solid_row())
    poor = configuration_subscore(
        _solid_row(free_percent=5.0, tiny_file_ratio=60.0, trim_enabled=False, mft_severity="critical")
    )
    assert good == 100.0
    assert poor < good
    assert poor >= 0.0


def test_configuration_subscore_none_when_no_signals():
    assert configuration_subscore({"host": "X"}) is None


def test_performance_subscore_bands():
    strong = performance_subscore(
        {"sequential_write": 1500, "sequential_read": 3000, "random_write": 120, "random_read": 400}
    )
    weak = performance_subscore(
        {"sequential_write": 50, "sequential_read": 200, "random_write": 5, "random_read": 40}
    )
    assert strong == 100.0
    assert weak == 25.0
    assert performance_subscore(None) is None


def test_score_machine_solid_is_high_and_not_capped():
    result = score_machine(_solid_row())
    assert result["score"] > 85
    assert result["fault_limited"] is False


def test_score_machine_critical_is_capped():
    result = score_machine(_solid_row(severity="CRITICAL"))
    assert result["raw_score"] > 25
    assert result["score"] == 25.0
    assert result["fault_limited"] is True


def test_score_machine_warning_is_capped():
    result = score_machine(_solid_row(severity="WARNING"))
    assert result["score"] == 60.0
    assert result["fault_limited"] is True


def test_storage_class_inference():
    assert storage_class({"bus": "NVMe", "media_type": "SSD"}) == "nvme"
    assert storage_class({"bus": "USB", "media_type": "Unspecified"}) == "usb"
    assert storage_class({"bus": "SATA", "media_type": "SSD"}) == "sata"
    assert storage_class({"bus": "RAID", "media_type": "SSD"}) == "nvme"


def test_resource_spec_scores_from_components_and_bus():
    scores = resource_spec_scores(_solid_row())
    assert scores["cpu"] == 100.0
    assert scores["memory"] == 100.0
    assert scores["gpu"] == 75.0
    assert scores["storage"] == 100.0  # NVMe class


def test_storage_expected_vs_actual_flags_underperformance():
    # DRAM-less NVMe: strong seq read but weak random/seq write vs NVMe class.
    row = _solid_row(
        benchmarks={
            "sequential_write": 264.0,
            "sequential_read": 619.0,
            "random_write": 42.0,
            "random_read": 129.0,
        }
    )
    result = storage_expected_vs_actual(row)
    assert result["available"] is True
    assert result["storage_class"] == "nvme"
    assert result["verdict"] in ("below", "well below")
    seq_write = next(t for t in result["tests"] if t["test"] == "sequential_write")
    assert seq_write["expected_mb_s"] == 1000.0
    assert seq_write["actual_mb_s"] == 264.0


def test_storage_expected_vs_actual_not_measured_without_benchmarks():
    result = storage_expected_vs_actual(_solid_row(benchmarks={}))
    assert result["available"] is False
    assert result["verdict"] == "not measured"


def test_rank_machines_orders_best_first_and_sinks_faults():
    good = _solid_row(host="GOOD")
    failing = _solid_row(host="FAIL", severity="CRITICAL")
    ranked = rank_machines([failing, good])
    assert ranked[0]["host"] == "GOOD"
    assert ranked[0]["rank"] == 1
    assert ranked[-1]["host"] == "FAIL"
    assert ranked[-1]["ranking"]["fault_limited"] is True


def test_rank_machines_unscored_go_last():
    scored = _solid_row(host="SCORED")
    bare = {"host": "BARE", "severity": "UNKNOWN"}
    ranked = rank_machines([bare, scored])
    assert ranked[0]["host"] == "SCORED"
    assert ranked[-1]["host"] == "BARE"
    assert ranked[-1]["ranking"]["score"] is None
