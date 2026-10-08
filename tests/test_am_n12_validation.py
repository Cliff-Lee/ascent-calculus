from experiments.am_n12_blind_search import run as run_blind_search
from experiments.am_n12_block_reconstruction import run as run_block_reconstruction
from experiments.am_n12_block_validation import validate as validate_block_independently
from experiments.am_n12_independent_validation import validate as validate_blind_independently


def test_generated_sweep_blindly_rediscovers_ordinary_to_modified_map():
    search = run_blind_search()
    assert search["classification"] == "blind_bounded_rediscovery"
    assert search["search_guidance"]["target_map_provided"] is False
    assert search["search_guidance"]["target_map_atom_enabled"] is False
    assert search["search_guidance"]["seeded_candidate"] is None
    assert search["candidate_space_exhausted"]
    assert search["generated_atom_count"] == 4
    assert search["candidates_tested"] == 5  # Identity plus the four generated sweep atoms.
    assert search["exact_candidate_count"] == len(search["finite_bijection_candidates"]) == 1
    assert search["finite_bijection_candidates"][0]["program"] == (
        "SweepLiftT(selector=RawAscTop(), inverse_lift=False, direction='ltr')"
    )

    validation = validate_blind_independently(search)
    assert validation["target_map_imported"] is False
    assert validation["production_class_generators_imported"] is False
    assert validation["training_degrees_rechecked"] == [1, 5]
    assert validation["held_out_degrees"] == [6, 7]
    assert [row["source_count"] for row in validation["degree_counts"]] == [1, 2, 5, 15, 53, 217, 1014]
    assert [row["target_count"] for row in validation["degree_counts"]] == [1, 2, 5, 15, 53, 217, 1014]
    assert validation["all_candidates_pass_training_window"]
    assert validation["any_candidate_passes_held_out_degrees"]
    assert validation["candidate_results"][0]["verified_through_degree"] == 7
    assert validation["proof_status"] == "not_proved"


def test_seeded_block_reconstruction_is_classified_separately_and_held_out():
    search = run_block_reconstruction()
    assert search["classification"] == "reconstruction_from_seeded_operations"
    assert search["search_guidance"]["reference_map_provided"] is False
    assert search["search_guidance"]["seeded_operations"] == [
        "increasing_runs", "reverse_complement", "max_pair_around_first",
    ]
    assert search["candidates_tested"] == 108
    assert len(search["finite_bijection_candidates"]) == 12

    validation = validate_block_independently(search)
    assert validation["target_map_imported"] is False
    assert validation["training_degrees_rechecked"] == [1, 4]
    assert validation["held_out_degrees"] == [5, 6]
    assert validation["all_candidates_pass_training_window"]
    assert sum(row["passes_held_out_degrees"] for row in validation["candidate_results"]) == 3
    assert validation["proof_status"] == "not_proved"
