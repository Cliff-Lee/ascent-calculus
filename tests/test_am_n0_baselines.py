from experiments.am_n0_baselines import (
    reproduce_ascent_shifted_map_search,
    reproduce_bijectionist_toolkit_rotation_example,
    reproduce_comb_ex_binary_word_examples,
    reproduce_findstat_matching_example,
    reproduce_near_bijection_failure,
)


def test_findstat_perfect_matching_example_reproduces_finite_distribution_data():
    result = reproduce_findstat_matching_example()

    assert result["all_levels_equidistributed"]
    assert result["total_object_inputs"] == 125
    assert [level["object_count"] for level in result["levels"]] == [1, 1, 3, 15, 105]
    assert result["levels"][-1]["nesting_distribution"] == {
        0: 14,
        1: 28,
        2: 28,
        3: 20,
        4: 10,
        5: 4,
        6: 1,
    }


def test_combinatorial_exploration_binary_word_examples_reproduce_counts_and_map_control():
    result = reproduce_comb_ex_binary_word_examples()

    assert result["reported_bb_sequence_reproduced"]
    assert result["avoiding_11_counts_n0_to_n10"] == [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    assert result["counts_equal"]
    assert result["recurrence_a_n_equals_a_n_minus_1_plus_a_n_minus_2"]
    assert result["source_objects_round_trip_checked"] == 19


def test_bijectionist_toolkit_rotation_example_reproduces_forced_statistic_values():
    result = reproduce_bijectionist_toolkit_rotation_example()

    assert result["permutation_count"] == 24
    assert result["rotation_fixed_permutations"] == [
        [1, 2, 3, 4],
        [2, 3, 4, 1],
        [3, 4, 1, 2],
        [4, 1, 2, 3],
    ]
    assert result["lis_distribution"] == {1: 1, 2: 13, 3: 9, 4: 1}
    assert result["values_forced_onto_fixed_points_by_orbit_parity"] == [1, 2, 3, 4]
    assert result["one_of_each_value_forced"]


def test_blind_ac_schema_search_goes_beyond_equal_count_vectors():
    result = reproduce_ascent_shifted_map_search(through=5)

    assert result["count_vectors_match"]
    assert result["source_counts"] == result["target_counts"] == [1, 2, 4, 10, 29]
    assert result["grammar_size"] == result["normalized_candidates_tested"] == 108
    assert result["reference_map_seeded"] is False
    assert len(result["finite_bijection_candidates"]) == 3
    assert len(result["candidates_agreeing_with_registered_map_on_every_source"]) == 3
    assert result["source_objects_checked_per_candidate"] == 46


def test_negative_control_reports_first_collision_instead_of_claiming_success():
    result = reproduce_near_bijection_failure()

    assert result["verified_through"] == 6
    assert result["first_failure"] == "collision"
    assert result["failure_degree"] == 7
    assert result["source_witness"] and result["image_witness"]
    assert len(result["collision_fibres"]) == result["missing_target_count"] == 2
    assert all(len(fibre["sources"]) == 2 for fibre in result["collision_fibres"])
