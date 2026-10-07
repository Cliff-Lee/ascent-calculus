import pytest

from ac.gui.experiments import browse_objects, find_unmatched_objects, parse_experiment, run_experiment, validate_pattern
from ac.core.word import ChainWord
from ac.patterns.classical import ClassicalPattern
from ac.gui.experiments import _pattern_present


def _side(family, mode="avoid", *patterns, offset=0):
    return {
        "family": family,
        "degree_offset": offset,
        "rules": [{"mode": mode, "pattern": p} for p in patterns],
    }


def test_pattern_validation_returns_standardized_cayley_notation():
    result = validate_pattern("2122")
    assert result["values"] == [2, 1, 2, 2]
    assert result["notation"] == "⟨2, 1, 2, 2⟩"
    with pytest.raises(ValueError, match="every level"):
        validate_pattern("214")


def test_fibre_pattern_fast_path_agrees_with_classical_occurrence_engine():
    for word in (ChainWord.of(values) for values in ((1,), (1, 2, 1, 2), (2, 1, 2, 2), (3, 1, 2, 3, 2))):
        for pattern in (ClassicalPattern("2122"), ClassicalPattern("2212")):
            assert _pattern_present(word, pattern) == pattern.compile().contains(word)


def test_experiment_model_represents_general_pattern_comparison():
    raw = {
        "question": "compare", "start": 1, "stop": 5, "statistic": "ascents",
        "left": _side("modified", "avoid", "2122", "122"),
        "right": _side("modified", "avoid", "2212"),
    }
    spec = parse_experiment(raw)
    assert spec.left.family == "modified"
    assert [rule.pattern.values for rule in spec.left.rules] == [(2, 1, 2, 2), (1, 2, 2)]
    assert spec.statistic == "ascents"


def test_generic_modified_2122_versus_2212_counts_match_through_degree_7():
    result = run_experiment({
        "question": "compare", "start": 1, "stop": 7,
        "left": _side("modified", "avoid", "2122"),
        "right": _side("modified", "avoid", "2212"),
    })
    assert result["all_counts_match"] is True
    assert [row["difference"] for row in result["rows"]] == [0] * 7
    assert result["finite_only"] is True
    assert result["headline"] == "Match through n=7"


def test_single_class_count_question_works_without_second_side():
    result = run_experiment({
        "question": "count", "start": 2, "stop": 2,
        "left": _side("ordinary", "contain", "12"),
    })
    assert result["rows"] == [{"n": 2, "left_degree": 2, "left_count": 1, "left_distribution": None}]
    assert result["specification"]["right"] is None


def test_comparison_reports_first_divergence_and_refined_distribution():
    result = run_experiment({
        "question": "compare", "start": 1, "stop": 3, "statistic": "ascents",
        "left": _side("ordinary", "avoid", "12"),
        "right": _side("ordinary", "avoid", "21"),
    })
    assert result["first_divergence"]["n"] == 2
    assert result["rows"][0]["distributions_match"] is True
    assert result["rows"][1]["distributions_match"] is False


def test_degree_shift_and_optional_structural_filter_are_serialized():
    result = run_experiment({
        "question": "compare", "start": 1, "stop": 3, "statistic": "maximum",
        "condition": {"statistic": "ascents", "operator": "ge", "value": 1},
        "left": _side("revised", "avoid", "3121", offset=1),
        "right": _side("ordinary", "avoid", "221"),
    })
    assert result["rows"][0]["left_degree"] == 2
    assert result["rows"][0]["right_degree"] == 1
    assert result["specification"]["condition"] == {"statistic": "ascents", "operator": "ge", "value": 1}


def test_family_specific_degree_safety_limits_are_enforced():
    with pytest.raises(ValueError, match="bounded to degree 7"):
        parse_experiment({
            "question": "count", "start": 1, "stop": 8,
            "left": _side("revised", "avoid", "3121"),
        })
    with pytest.raises(ValueError, match="general length-4 pattern searches.*degree 8"):
        parse_experiment({
            "question": "count", "start": 1, "stop": 9,
            "left": _side("modified", "avoid", "3121"),
        })


def test_object_browser_returns_members_and_structural_statistics_from_the_selected_class():
    result = run_experiment({
        "question": "count", "start": 2, "stop": 2,
        "left": _side("ordinary", "avoid", "12"),
    })
    page = browse_objects(result["specification"], "left", 2, limit=10)
    assert page["degree"] == 2
    assert [item["word"] for item in page["objects"]] == [[1, 1]]
    assert page["objects"][0]["ascents"] == 0
    assert page["objects"][0]["multiplicity_partition"] == [2]
    assert page["next_offset"] is None


def test_first_divergence_returns_exact_set_difference_witnesses():
    result = run_experiment({
        "question": "compare", "start": 1, "stop": 3,
        "left": _side("ordinary", "avoid", "12"),
        "right": _side("ordinary", "avoid", "21"),
    })
    witness_result = find_unmatched_objects(result["specification"], 2)
    assert witness_result["exact"] is True
    assert witness_result["left_only"] is None
    assert witness_result["right_only"]["word"] == [1, 2]
    assert witness_result["tested_objects"] == 2


def test_unmatched_search_explains_when_degree_shift_makes_objects_incomparable():
    with pytest.raises(ValueError, match="same family and degree"):
        find_unmatched_objects({
            "question": "compare", "start": 1, "stop": 2,
            "left": _side("ordinary", "avoid", "12"),
            "right": _side("ordinary", "avoid", "21", offset=1),
        }, 1)


def test_object_browser_pages_keep_exact_class_ranks():
    spec = {
        "question": "count", "start": 1, "stop": 4,
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    first = browse_objects(spec, "left", 4, offset=0, limit=2)
    second = browse_objects(spec, "left", 4, offset=2, limit=2)
    assert [item["index"] for item in first["objects"]] == [1, 2]
    assert first["next_offset"] == 2
    assert [item["index"] for item in second["objects"]] == [3, 4]
    for item in first["objects"] + second["objects"]:
        assert [value for block in item["run_blocks"] for value in block] == item["word"]
        assert len(item["run_blocks"]) == len(item["run_start_positions"])


def test_object_browser_combines_statistic_and_pattern_filters_exactly():
    spec = {
        "question": "count", "start": 1, "stop": 3,
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    page = browse_objects(spec, "left", 3, limit=20, filters={
        "statistic": "ascents", "value": "1", "pattern_mode": "contain", "pattern": "12",
    })
    words = [item["word"] for item in page["objects"]]
    assert words == [[1, 1, 2], [1, 2, 1], [1, 2, 2]]
    assert all(item["ascents"] == 1 for item in page["objects"])
    assert page["filters_active"] is True
    assert page["filter_summary"]["pattern"] == [1, 2]


def test_filtered_object_browser_pages_use_filtered_result_ranks():
    spec = {
        "question": "count", "start": 1, "stop": 3,
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    filters = {"statistic": "ascents", "value": "1"}
    first = browse_objects(spec, "left", 3, limit=2, filters=filters)
    second = browse_objects(spec, "left", 3, offset=2, limit=2, filters=filters)
    assert [item["index"] for item in first["objects"]] == [1, 2]
    assert [item["index"] for item in second["objects"]] == [3]
    assert second["next_offset"] is None


def test_object_browser_supports_list_valued_occurrence_profile_filter():
    spec = {
        "question": "count", "start": 1, "stop": 3,
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    page = browse_objects(spec, "left", 3, limit=20, filters={
        "statistic": "multiplicity_partition", "value": "2,1",
    })
    assert all(item["multiplicity_partition"] == [2, 1] for item in page["objects"])
    assert page["objects"]


def test_ascent_run_count_is_available_as_a_refinement_and_browser_filter():
    spec = {
        "question": "count", "start": 1, "stop": 3, "statistic": "ascent_runs",
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    result = run_experiment(spec)
    assert result["statistic_label"] == "Number of ascent runs"
    page = browse_objects(result["specification"], "left", 3, limit=20, filters={
        "statistic": "ascent_runs", "value": "2",
    })
    assert [item["word"] for item in page["objects"]] == [[1, 1, 2], [1, 2, 1], [1, 2, 2]]


def test_run_start_position_profile_refines_and_filters_block_boundaries():
    spec = {
        "question": "compare", "start": 1, "stop": 3, "statistic": "run_start_positions",
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
        "right": {"family": "ordinary", "degree_offset": 0, "rules": [{"mode": "avoid", "pattern": "12"}]},
    }
    result = run_experiment(spec)
    assert result["statistic_label"] == "Ascent-run start positions"
    page = browse_objects(result["specification"], "left", 3, limit=10, filters={
        "statistic": "run_start_positions", "value": "1,3",
    })
    assert [item["word"] for item in page["objects"]] == [[1, 2, 1], [1, 2, 2]]
    assert all(item["run_start_positions"] == [1, 3] for item in page["objects"])


def test_last_occurrence_profile_distinguishes_words_with_the_same_first_profile():
    spec = {
        "question": "count", "start": 1, "stop": 4, "statistic": "last_occurrence_positions",
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    result = run_experiment(spec)
    assert result["statistic_label"] == "Last-occurrence positions"
    page = browse_objects(result["specification"], "left", 4, limit=10, filters={
        "statistic": "last_occurrence_positions", "value": "2,4",
    })
    assert [item["word"] for item in page["objects"]] == [[1, 1, 2, 2], [1, 2, 1, 1]]
    assert page["objects"][1]["first_occurrence_positions"] == [1, 2]
    assert all(item["last_occurrence_positions"] == [2, 4] for item in page["objects"])


def test_run_length_composition_is_a_refinement_and_exact_object_filter():
    spec = {
        "question": "count", "start": 1, "stop": 4, "statistic": "run_lengths",
        "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
    }
    result = run_experiment(spec)
    assert result["statistic_label"] == "Ascent-run lengths"
    page = browse_objects(result["specification"], "left", 4, limit=10, filters={
        "statistic": "run_lengths", "value": "2,1,1",
    })
    assert page["objects"]
    assert all(item["run_lengths"] == [2, 1, 1] for item in page["objects"])
    assert all(len(item["run_blocks"]) == 3 for item in page["objects"])


def test_object_browser_applies_general_pattern_degree_bound_to_extra_filters():
    with pytest.raises(ValueError, match="bounded to degree 8"):
        browse_objects({
            "question": "count", "start": 1, "stop": 9,
            "left": {"family": "ordinary", "degree_offset": 0, "rules": []},
        }, "left", 9, filters={"pattern_mode": "contain", "pattern": "1234"})
