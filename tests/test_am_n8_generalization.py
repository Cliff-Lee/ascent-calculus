import json
import tempfile
import time
from pathlib import Path

from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import TransformationGrammarSpec, TransformationSearchSpec
from ac.discovery.transformation_family import (
    FAMILY_SEARCH_VERSION,
    TransformationFamilySearchSpec,
    run_worker_search,
)
from ac.discovery.research_memory import ResearchMemoryStore
from ac.discovery.worker import PersistentWorker


def _grammar():
    return TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=2, max_steps=2,
        candidate_budget=50, expansion_budget=500,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=1_000_000,
    )


def _family_spec():
    grammar = _grammar()
    degree_window = DegreeWindow(1, 3)
    modified_111 = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
    scenarios = (
        TransformationSearchSpec(ClassSpec("ordinary"), ClassSpec("ordinary"), degree_window, grammar),
        TransformationSearchSpec(modified_111, modified_111, degree_window, grammar),
        TransformationSearchSpec(
            ClassSpec("ordinary"), ClassSpec("ordinary"), degree_window, grammar,
            source_offset=0, target_offset=1,
        ),
    )
    return TransformationFamilySearchSpec(
        scenarios, candidate_budget=50, enumeration_budget=500_000,
        class_object_budget=100_000, evaluation_budget=1_000_000,
    )


def _wait_for(store, job_id, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        job = store.get_job(job_id)
        if job.status in {"completed", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for family search; state={store.get_job(job_id)}")


def test_class_offset_grid_is_canonical_and_round_trips():
    grammar = _grammar()
    classes = (
        ClassSpec("ordinary"),
        ClassSpec.build("ordinary", [{"mode": "avoid", "pattern": "11"}]),
    )
    spec = TransformationFamilySearchSpec.from_grid(
        classes, classes, DegreeWindow(1, 2), grammar,
        offset_pairs=((0, 0), (0, 1)), candidate_budget=30,
        enumeration_budget=200_000, class_object_budget=50_000,
        evaluation_budget=100_000,
    )
    assert len(spec.scenarios) == 8
    restored = TransformationFamilySearchSpec.from_dict(json.loads(spec.canonical_json()))
    assert restored == spec
    assert restored.fingerprint == spec.fingerprint
    assert {scenario.degree_shift for scenario in restored.scenarios} == {0, 1}


def test_family_search_finds_class_reuse_and_reports_offset_failures_with_resume():
    spec = _family_spec()
    job = type("Job", (), {"question": spec, "checkpoint": {}})()

    class Context:
        def __init__(self):
            self.checkpoints = []

        def checkpoint(self, state, progress):
            self.checkpoints.append((json.loads(json.dumps(state)), dict(progress)))

        def check_control(self):
            pass

    context = Context()
    result = run_worker_search(job, context)
    assert result["family_search_version"] == FAMILY_SEARCH_VERSION
    assert result["degree_shifts_searched"] == [0, 1]
    assert result["scenario_count"] == 3
    assert result["scenario_match_counts"][0] >= 1
    assert result["scenario_match_counts"][1] >= 1
    assert result["scenario_match_counts"][2] == 0
    identity = next(row for row in result["ranked_candidates"] if row["program"] == "Identity()")
    assert identity["matching_scenario_count"] == 2
    assert identity["bijection_on_every_scenario"] is False
    assert identity["proof_status"] == "not_proved"

    saved = context.checkpoints[-1][0]
    resumed_job = type("Job", (), {"question": spec, "checkpoint": saved})()
    resumed = run_worker_search(resumed_job, Context())
    for key in (
        "candidates_tested", "exact_candidate_count", "exact_candidates",
        "ranked_candidates", "scenario_match_counts", "candidate_space_exhausted",
    ):
        assert resumed[key] == result[key]


def test_family_job_round_trips_through_persistent_worker_dispatch():
    spec = _family_spec()
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        job = store.create_job(spec, handler="search-transformation-families")
        assert store.get_job(job.id).question == spec
        worker = PersistentWorker(store.path, idle_poll_seconds=0.02, stale_after_seconds=0.2)
        try:
            worker.start()
            completed = _wait_for(store, job.id)
            assert completed.status == "completed", completed.error
            assert completed.result["status"] == "finite_cross_scenario_search"
            assert completed.result["scenario_count"] == 3
            assert completed.result["research_memory"]["status"] == "recorded"
            memory = ResearchMemoryStore(Path(directory) / "research-memory.sqlite3")
            assert memory.get_run(job.id)["novelty"]["candidate_count"] > 0
        finally:
            worker.stop()
