import json

from ac.core.word import ChainWord
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.synthesis import FailureKind, SynthesisFailure, _word_key
from ac.discovery.transformation_search import (
    CEGIS_VERSION,
    TransformationGrammarSpec,
    TransformationSearchSpec,
    _counterexample_id,
    _counterexample_record,
    _minimize_counterexample,
    _replay_counterexample,
    _witness_failure_for_pair,
    _witness_failure_for_word,
    run_transformation_search,
)
from ac.generate.universes import ascent_sequences
from ac.transform.basic import TransformResult
from ac.algebra.transforms import Transformation
from ac.algebra.transforms import Identity


class _RaiseFirstAboveOne(Transformation):
    def apply(self, word):
        values = (word.height + 1,) + word.values[1:]
        output = ChainWord.of(values)
        return TransformResult(output, tuple(range(1, len(word) + 1)))


class _CollapseToOnes(Transformation):
    def apply(self, word):
        output = ChainWord.of((1,) * len(word))
        return TransformResult(output, tuple(range(1, len(word) + 1)))


def test_counterexample_minimizer_returns_source_class_lowering_minimal_word():
    spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("ordinary"), DegreeWindow(1, 3),
        TransformationGrammarSpec(
            operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
            max_selectors=20, max_atoms=20, max_cost=2, max_steps=1,
            candidate_budget=20, expansion_budget=100,
        ),
    )
    words = tuple(ascent_sequences(3))
    target_keys = frozenset(_word_key(word) for word in words)
    data = {3: (words, words, target_keys)}
    transform = _RaiseFirstAboveOne()
    source = ChainWord.of((1, 2, 2))
    initial = _witness_failure_for_word(transform, source, 3, target_keys)
    assert initial is not None and initial.kind is FailureKind.OUTSIDE_TARGET

    minimized = _minimize_counterexample(transform, initial, spec, data)
    assert minimized.source.values == (1, 1, 1)
    assert minimized.kind is FailureKind.OUTSIDE_TARGET
    for index, value in enumerate(minimized.source.values):
        for replacement in range(1, value):
            values = list(minimized.source.values)
            values[index] = replacement
            candidate = ChainWord.of(values)
            if spec.source.predicate().holds(candidate):
                assert _witness_failure_for_word(transform, candidate, 3, target_keys) is None


def test_collision_pair_is_a_replayable_counterexample_constraint():
    spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("ordinary"), DegreeWindow(1, 2),
        TransformationGrammarSpec(
            operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
            max_selectors=20, max_atoms=20, max_cost=2, max_steps=1,
            candidate_budget=20, expansion_budget=100,
        ),
    )
    words = tuple(ascent_sequences(2))
    target_keys = frozenset(_word_key(word) for word in words)
    data = {2: (words, words, target_keys)}
    first, second = ChainWord.of((1, 1)), ChainWord.of((1, 2))
    transform = _CollapseToOnes()
    failure = _witness_failure_for_pair(transform, first, second, 2, target_keys)
    assert failure is not None and failure.kind is FailureKind.COLLISION
    minimized = _minimize_counterexample(transform, failure, spec, data)
    assert minimized.source.values != minimized.other_source.values
    witness_id = _counterexample_id(minimized)
    witness = _counterexample_record(minimized, transform, 3, witness_id)
    assert _replay_counterexample(
        transform, witness, data, unverified_through=0,
    ).failure.kind is FailureKind.COLLISION
    assert _replay_counterexample(
        Identity(), witness, data, unverified_through=0,
    ) is None


def test_transformation_worker_replays_refined_counterexamples_and_checkpoints_them():
    grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=4, max_steps=3,
        candidate_budget=100, expansion_budget=1_000, evaluation_budget=10_000,
    )
    spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("ordinary"), DegreeWindow(1, 4), grammar,
    )
    job = type("Job", (), {"question": spec, "checkpoint": {}})()

    class Context:
        def __init__(self):
            self.checkpoints = []

        def checkpoint(self, state, progress):
            snapshot = json.loads(json.dumps(state))
            self.checkpoints.append((snapshot, dict(progress)))

        def check_control(self):
            pass

    context = Context()
    result = run_transformation_search(job, context)
    cegis = result["counterexample_guided_evaluation"]
    assert cegis["version"] == CEGIS_VERSION
    assert cegis["refinement_round_count"] > 0
    assert cegis["screened_candidate_count"] > 0
    assert cegis["fully_evaluated_candidate_count"] > 0
    assert cegis["counterexample_suite"]
    assert cegis["refinement_trace"][0]["counterexample_id"] == cegis["counterexample_suite"][0]["id"]
    assert all(
        witness["minimality"].startswith("single-entry-lowering-minimal")
        for witness in cegis["counterexample_suite"]
    )

    replayed = [row for row in result["near_misses"] if row["evaluation_mode"] == "counterexample_replay"]
    assert replayed
    assert all("counterexample" in row and "first_failure" not in row for row in replayed)
    assert all(row["verified_through"] == spec.degrees.start - 1 for row in replayed)
    if context.checkpoints:
        saved = next(
            state for state, _ in context.checkpoints
            if state.get("cegis_version") == CEGIS_VERSION and state.get("counterexample_suite")
        )
        progress = next(
            progress for state, progress in context.checkpoints if state is saved
        )
        assert progress["counterexample_refinements"] == len(saved["cegis_trace"])
        resumed_job = type("Job", (), {"question": spec, "checkpoint": saved})()
        resumed = run_transformation_search(resumed_job, Context())
        for key in (
            "candidates_tested", "exact_candidate_count", "exact_candidates",
            "near_misses", "candidate_space_exhausted", "counterexample_guided_evaluation",
        ):
            assert resumed[key] == result[key]
