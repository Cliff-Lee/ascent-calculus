import tempfile
from pathlib import Path

from ac.discovery.research_memory import ResearchMemoryStore
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import (
    TransformationGrammarSpec,
    TransformationSearchSpec,
    run_transformation_search,
)


def _question(*, source=None, target=None, degrees=DegreeWindow(1, 2)):
    grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=2, max_steps=2,
        candidate_budget=50, expansion_budget=500,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=1_000_000,
    )
    return TransformationSearchSpec(
        source or ClassSpec("ordinary"),
        target or ClassSpec("ordinary"),
        degrees,
        grammar,
    )


def test_memory_tracks_new_programs_finite_duplicates_reuse_and_idempotency():
    question = _question()
    identity = {
        "program": "Identity()",
        "finite_match_through_window": True,
        "finite_map_fingerprint": "a" * 64,
        "verified_through": 2,
        "proof_status": "not_proved",
    }
    alias = {**identity, "program": "IdentityAlias()"}
    with tempfile.TemporaryDirectory() as directory:
        memory = ResearchMemoryStore(Path(directory) / "memory.sqlite3")
        first = memory.record_result(
            question, {"exact_candidates": [identity], "near_misses": []},
            run_id="run-1", provenance={"classification": "bounded_reconstruction"},
        )
        assert first["novelty_counts"]["new_transformation"] == 1
        assert first["candidates"][0]["novelty"] == "new_transformation"

        second = memory.record_result(
            question, {"exact_candidates": [identity], "near_misses": [alias]},
            run_id="run-2",
        )
        assert second["novelty_counts"]["exact_program_duplicate"] == 1
        assert second["novelty_counts"]["same_finite_map"] == 1
        assert {item["novelty"] for item in second["candidates"]} == {
            "exact_program_duplicate", "same_finite_map",
        }

        different_question = _question(
            source=ClassSpec.build("ordinary", [{"mode": "avoid", "pattern": "11"}]),
        )
        third_result = memory.record_result(
            different_question, {"exact_candidates": [identity], "near_misses": []},
            run_id="run-3",
        )
        assert third_result["candidates"][0]["novelty"] == "new_application_of_known_transformation"

        retry = memory.record_result(
            different_question, {"exact_candidates": [identity], "near_misses": []},
            run_id="run-3",
        )
        assert retry["idempotent"] is True
        candidate_id = first["candidates"][0]["candidate_id"]
        assert len(memory.candidate_history(candidate_id)) == 3
        assert len(memory.recent_runs(limit=10)) == 3
        assert memory.get_run("run-1")["classification"] == "bounded_reconstruction"


def test_search_emits_repeatable_finite_map_fingerprint_for_exact_programs():
    spec = _question()
    job = type("Job", (), {"question": spec, "checkpoint": {}})()

    class Context:
        def checkpoint(self, state, progress):
            pass

        def check_control(self):
            pass

    first = run_transformation_search(job, Context())
    second = run_transformation_search(job, Context())
    identity_first = next(row for row in first["exact_candidates"] if row["program"] == "Identity()")
    identity_second = next(row for row in second["exact_candidates"] if row["program"] == "Identity()")
    assert len(identity_first["finite_map_fingerprint"]) == 64
    assert identity_first["finite_map_fingerprint"] == identity_second["finite_map_fingerprint"]
