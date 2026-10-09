import tempfile
import time
from pathlib import Path

from ac.algebra.block_schemas import BlockSchemaT
from ac.algebra.transforms import InsertFreshMaximumT, ReverseT, SweepLiftT
from ac.core.word import ChainWord
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import (
    TransformationGrammarSpec,
    TransformationSearchSpec,
    generate_transformation_atoms,
    iter_typed_transform_programs,
)
from ac.discovery.worker import PersistentWorker
from ac.logic.selectors import AscBottom, AscTop, Before, RawAscTop, ScopeFirst


def _wait_for(store, job_id, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        job = store.get_job(job_id)
        if job.status in {"completed", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for transformation search; state={store.get_job(job_id)}")


def test_fresh_maximum_cut_insertion_preserves_snapshot_positions():
    word = ChainWord.of([1, 2])
    result = InsertFreshMaximumT(Before(ScopeFirst())).apply(word)
    assert result.output.values == (3, 1, 2)
    assert result.output.height == 3
    assert result.position_map == (2, 3)
    assert result.created_positions == (1,)
    assert result.output.position_ids == (-1, 1, 2)

    # An empty event set adds neither a position nor a new ambient level.
    descending = ChainWord.of([2, 1])
    untouched = InsertFreshMaximumT(Before(RawAscTop())).apply(descending)
    assert untouched.output.values == descending.values
    assert untouched.output.height == descending.height


def test_generated_grammar_has_selector_sweeps_and_stable_serialized_spec():
    grammar = TransformationGrammarSpec(
        operations=("selector_sweeps", "symmetry"),
        selectors=("asc_top", "asc_bottom", "repeat"),
        boolean_selector_algebra=True,
        position_bound=3,
        max_selectors=100,
        max_atoms=1_000,
        max_cost=2,
        max_steps=2,
        candidate_budget=100,
        expansion_budget=10_000,
    )
    atoms = generate_transformation_atoms(grammar)
    assert any(isinstance(atom, SweepLiftT) and isinstance(atom.selector, AscTop) for atom in atoms)
    assert any(isinstance(atom, SweepLiftT) and isinstance(atom.selector, AscBottom) for atom in atoms)
    assert any("SetBinary" in repr(atom.selector) for atom in atoms if isinstance(atom, SweepLiftT))

    spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("revised"), DegreeWindow(1, 3), grammar,
        source_offset=0, target_offset=2,
    )
    restored = TransformationSearchSpec.from_dict(spec.to_dict())
    assert restored == spec
    assert restored.fingerprint == spec.fingerprint
    assert restored.degree_shift == 2


def test_degree_shift_pruning_keeps_unknown_effects_for_exact_evaluation():
    fresh = InsertFreshMaximumT(Before(ScopeFirst()))
    block = BlockSchemaT(
        "increasing_runs", "none", "stable", "identity", "max_pair_around_first",
    )
    programs = tuple(iter_typed_transform_programs(
        (ReverseT(), fresh, block),
        max_cost=4,
        max_steps=1,
        expected_length_shift=2,
        max_candidates=10,
        expansion_budget=100,
    ))
    assert ReverseT() not in programs  # known length-preserving effect, wrong shift
    assert fresh in programs  # unknown effect is retained for objectwise checks
    assert block in programs  # known +2 effect matches the requested offset


def test_registered_worker_searches_a_class_map_and_reports_only_finite_evidence():
    grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=2, max_steps=2,
        candidate_budget=20, expansion_budget=100, evaluation_budget=16,
    )
    spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("ordinary"), DegreeWindow(1, 3), grammar,
    )
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        job = store.create_job(spec, handler="search-transformations")
        assert store.get_job(job.id).question == spec
        worker = PersistentWorker(store.path, idle_poll_seconds=0.02, stale_after_seconds=0.2)
        try:
            worker.start()
            completed = _wait_for(store, job.id)
            assert completed.status == "completed", completed.error
            result = completed.result
            assert result["status"] == "finite_computational_search"
            assert result["candidate_space_exhausted"] is False
            assert result["effective_candidate_budget"] == 2
            assert result["evaluation_budget_limited"] is True
            assert result["source_class_objects"] == 8
            assert result["exact_candidate_count"] >= 1
            assert result["exact_candidates"][0]["program"] == "Identity()"
            assert all(row["proof_status"] == "not_proved" for row in result["exact_candidates"])
            assert "prove injectivity and surjectivity" in result["proof_obligations"][2]
        finally:
            worker.stop()
