import pytest
from threading import Event

from ac.gui.transform_experiments import run_transform_experiment


def _side(family, mode="none", pattern=""):
    rules = [] if mode == "none" else [{"mode": mode, "pattern": pattern}]
    return {"family": family, "rules": rules}


def test_hat_audits_as_a_finite_bijection_from_ordinary_to_modified_through_degree_6():
    result = run_transform_experiment({
        "transformation": "hat", "start": 1, "stop": 6, "statistic": "ascents",
        "source": _side("ordinary"), "target": _side("modified"),
    })
    assert result["finite_only"] is True
    assert result["evidence"]["status"] == "verified"
    assert result["evidence"]["schema"] == "ac.finite-result.v1"
    for row in result["rows"]:
        assert row["source_count"] == row["target_count"]
        assert row["cayley_outputs"] == row["source_count"]
        assert row["target_hits"] == row["source_count"]
        assert row["distinct_images"] == row["source_count"]
        assert row["collisions"] == 0
        assert row["target_coverage"] == row["target_count"]
        assert row["inverse_successes"] == row["source_count"]
        assert row["statistic_failures"] == 0


def test_reverse_reports_a_target_class_failure_and_a_reproducible_witness():
    result = run_transform_experiment({
        "transformation": "reverse", "start": 1, "stop": 2,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][-1]
    assert row["all_sources_land_in_target"] is False
    assert row["first_target_failure"] == {"source": [1, 2], "output": [2, 1]}
    assert row["injective"] is True
    assert row["surjective"] is False
    assert result["evidence"]["status"] == "counterexample"


def test_transform_experiment_can_be_cancelled_without_recording_partial_degree():
    cancellation = Event()
    updates = []

    def stop_after_first_degree(update):
        updates.append(update)
        if update["phase"] == "degree_complete" and update["degree"] == 1:
            cancellation.set()

    result = run_transform_experiment({
        "transformation": "reverse", "start": 1, "stop": 4,
        "source": _side("ordinary"), "target": _side("ordinary"),
    }, progress=stop_after_first_degree, cancel_event=cancellation)

    assert [row["n"] for row in result["rows"]] == [1]
    assert result["evidence"]["status"] == "incomplete"
    assert result["evidence"]["complete"] is False
    assert result["evidence"]["cancelled_at_degree"] == 2
    assert updates[-1]["phase"] == "cancelled"


def test_source_pattern_restrictions_are_applied_before_the_transformation():
    result = run_transform_experiment({
        "transformation": "reverse", "start": 1, "stop": 4,
        "source": _side("ordinary", "avoid", "12"),
        "target": _side("ordinary"),
    })
    assert result["rows"][-1]["source_count"] < 15
    assert result["specification"]["source"]["rules"][0]["pattern"] == [1, 2]


def test_transformation_degree_limit_is_enforced():
    with pytest.raises(ValueError, match="bounded to degrees 1–10"):
        run_transform_experiment({
            "transformation": "hat", "start": 1, "stop": 11,
            "source": _side("ordinary"), "target": _side("modified"),
        })


def test_partial_inverse_hat_reports_a_finite_target_miss():
    result = run_transform_experiment({
        "transformation": "inverse_hat", "start": 5, "stop": 5,
        "source": _side("modified"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert row["source_count"] == 53
    assert row["target_hits"] == 52
    assert row["first_target_failure"] is not None


def test_statistic_transport_reports_a_counterexample_witness():
    result = run_transform_experiment({
        "transformation": "reverse", "start": 2, "stop": 2, "statistic": "ascents",
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert row["statistic_failures"] == 1
    assert row["first_statistic_failure"] == {
        "source": [1, 2], "output": [2, 1], "source_value": 1, "output_value": 0,
    }


def test_prefix_lift_parameter_is_recorded_and_inverse_recovers_each_source():
    result = run_transform_experiment({
        "transformation": "prefix_lift", "parameter": 4, "start": 4, "stop": 4,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert result["parameter"] == 4
    assert result["specification"]["parameter"] == 4
    assert row["first_invalid"] is None
    assert row["inverse_successes"] == row["source_count"]


def test_prefix_lift_reports_out_of_range_pivots_as_source_witnesses():
    result = run_transform_experiment({
        "transformation": "prefix_lift", "parameter": 4, "start": 3, "stop": 3,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert row["source_count"] == 5
    assert row["cayley_outputs"] == 0
    assert row["first_invalid"] == {
        "source": [1, 1, 1], "reason": "IndexError: 4",
    }


def test_inverse_prefix_lift_exposes_its_first_occurrence_precondition():
    result = run_transform_experiment({
        "transformation": "inverse_prefix_lift", "parameter": 3,
        "start": 3, "stop": 3,
        "source": _side("modified"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert row["source_count"] > 0
    assert row["first_invalid"] is not None
    assert "first occurrence" in row["first_invalid"]["reason"]


def test_parameterized_transform_rejects_invalid_pivot_positions():
    with pytest.raises(ValueError, match="positive integer"):
        run_transform_experiment({
            "transformation": "prefix_lift", "parameter": 0,
            "source": _side("ordinary"), "target": _side("ordinary"),
        })
    with pytest.raises(ValueError, match="whole number"):
        run_transform_experiment({
            "transformation": "prefix_lift", "parameter": 1.5,
            "source": _side("ordinary"), "target": _side("ordinary"),
        })


def test_position_insertion_checks_n_to_n_plus_one_and_deletes_its_created_entry():
    result = run_transform_experiment({
        "transformation": "insert_position", "parameter": 2, "value": 1,
        "start": 2, "stop": 2,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert (row["source_degree"], row["target_degree"]) == (2, 3)
    assert row["source_count"] == 2
    assert row["cayley_outputs"] == 2
    assert row["inverse_successes"] == 2
    assert result["specification"]["target"]["degree_offset"] == 1


def test_deleting_a_position_checks_n_to_n_minus_one_and_retains_ambient_levels():
    result = run_transform_experiment({
        "transformation": "delete_position", "parameter": 2, "value": 1,
        "start": 2, "stop": 2,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert (row["source_degree"], row["target_degree"]) == (2, 1)
    assert row["target_count"] == 1
    assert row["distinct_images"] == 2
    assert row["collisions"] == 0
    assert row["cayley_outputs"] == 1
    assert row["inverse_successes"] == 1
    assert row["first_inverse_failure"]["source"] == [1, 2]


def test_restriction_position_outside_some_source_words_is_a_witness():
    result = run_transform_experiment({
        "transformation": "delete_position", "parameter": 4, "value": 1,
        "start": 2, "stop": 2,
        "source": _side("ordinary"), "target": _side("ordinary"),
    })
    row = result["rows"][0]
    assert row["first_invalid"] == {"source": [1, 1], "reason": "IndexError: 4"}


def test_position_insertion_requires_a_value_level():
    with pytest.raises(ValueError, match="value level"):
        run_transform_experiment({
            "transformation": "insert_position", "parameter": 0,
            "source": _side("ordinary"), "target": _side("ordinary"),
        })
