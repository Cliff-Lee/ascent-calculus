from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile

from ac.discovery.dossiers import build_research_dossier, read_dossier, validate_dossier, write_dossier
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.conjecture_search import ConjectureSearchSpec
from ac.discovery.specification import ClassSpec, DegreeWindow, SearchSpec
from ac.discovery.transformation_search import TransformationGrammarSpec, TransformationSearchSpec
from ac.discovery.transformation_family import TransformationFamilySearchSpec


def _question():
    grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        position_bound=2, occurrence_rank=1, inserted_value_bound=1,
        max_selectors=20, max_atoms=20, max_cost=2, max_steps=1,
        candidate_budget=20, expansion_budget=200,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=500_000,
    )
    return TransformationSearchSpec(
        ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}]),
        ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}]),
        DegreeWindow(1, 3), grammar, target_offset=2,
    )


def test_dossier_round_trip_preserves_question_result_checkpoint_and_history():
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        job = store.create_job(_question(), handler="search-transformations")
        result = {
            "status": "finite_transformation_search",
            "proof_status": "not_proved",
            "candidates_tested": 7,
            "scenario_count": 1,
            "exact_candidates": [{"program": "Identity()", "example_map_preview": {"source": [1], "output": [1]}}],
            "near_misses": [{"first_failure": {"kind": "outside_target", "base_degree": 3}}],
            "proof_obligations": ["prove the map for all degrees"],
        }
        paused = replace(
            job,
            status="paused",
            checkpoint={"next_candidate_index": 7, "candidate_suite": [{"source": [1, 2]}]},
            progress={"stage": "testing", "candidates_tested": 7},
        )
        dossier = build_research_dossier(
            replace(paused, result=result),
            events=({"seq": 1, "event": "paused", "details": {"cursor": 7}, "created_at": 1.0},),
        )
        assert dossier["mathematical_question"]["fingerprint"] == job.question.fingerprint
        assert json.loads(dossier["mathematical_question"]["canonical_json"]) == job.question.to_dict()
        assert dossier["mathematical_question"]["semantics_definition"]["modified_ascent_sequence"]
        assert len(dossier["mathematical_question"]["semantics_fingerprint"]) == 64
        assert dossier["tested_bounds"]["planned_degree_windows"][0]["stop"] == 3
        assert dossier["tested_bounds"]["candidate_budget"] == 20
        assert dossier["execution"]["checkpoint"] == paused.checkpoint
        assert dossier["execution"]["events"][0]["event"] == "paused"
        assert dossier["finite_result"] == result
        assert dossier["proof_status"] == "not_proved"

        destination = write_dossier(Path(directory) / "study.json", dossier)
        restored = read_dossier(destination)
        assert restored == dossier
        assert not list(Path(directory).glob("*.tmp"))


def test_dossier_validation_rejects_changed_specification_or_fingerprint():
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        job = store.create_job(_question(), handler="search-transformations")
        dossier = build_research_dossier(job)

    changed_spec = deepcopy(dossier)
    changed_spec["mathematical_question"]["specification"]["degrees"]["stop"] = 4
    try:
        validate_dossier(changed_spec)
    except ValueError as exc:
        assert "canonical specification" in str(exc)
    else:
        raise AssertionError("changed mathematical question was accepted")

    changed_fingerprint = deepcopy(dossier)
    changed_fingerprint["mathematical_question"]["fingerprint"] = "0" * 64
    try:
        validate_dossier(changed_fingerprint)
    except ValueError as exc:
        assert "fingerprint" in str(exc)
    else:
        raise AssertionError("mismatched fingerprint was accepted")

    changed_semantics = deepcopy(dossier)
    changed_semantics["mathematical_question"]["semantics_definition"]["evidence_status"] = "proved"
    try:
        validate_dossier(changed_semantics)
    except ValueError as exc:
        assert "semantics fingerprint" in str(exc)
    else:
        raise AssertionError("changed semantics definition was accepted")


def test_dossier_export_captures_open_checkpoint_without_claiming_completion():
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        job = store.create_job(_question(), handler="search-transformations")
        pending = replace(
            job,
            status="interrupted",
            checkpoint={"next_candidate_index": 12},
            progress={"stage": "testing", "candidates_tested": 12},
        )
        dossier = build_research_dossier(pending)
    assert dossier["execution"]["status"] == "interrupted"
    assert dossier["execution"]["checkpoint"]["next_candidate_index"] == 12
    assert dossier["tested_bounds"]["candidates_tested"] == 12
    assert dossier["proof_status"] == "not_proved"
    assert "finite computation" in dossier["interpretation"]


def test_dossier_reader_validates_each_registered_research_question_format():
    degree_window = DegreeWindow(1, 2)
    ordinary = ClassSpec("ordinary")
    revised = ClassSpec("revised")
    search = SearchSpec("count_equivalence", ordinary, degree_window, revised)
    conjectures = ConjectureSearchSpec.build(families=("ordinary",), start=1, stop=2, pattern_lengths=(2,))
    family = TransformationFamilySearchSpec.from_grid(
        (ordinary, revised), (ordinary,), degree_window, _question().grammar,
        offset_pairs=((0, 0),), candidate_budget=20,
        enumeration_budget=100_000, class_object_budget=100_000,
        evaluation_budget=500_000,
    )
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        for index, question in enumerate((search, conjectures, family)):
            job = store.create_job(question, handler=f"format-{index}")
            dossier = build_research_dossier(job)
            assert validate_dossier(dossier)["mathematical_question"]["fingerprint"] == question.fingerprint
            if isinstance(question, TransformationFamilySearchSpec):
                assert dossier["tested_bounds"]["search_budgets"]["max_cost"] == question.grammar.max_cost
                assert dossier["tested_bounds"]["search_budgets"]["expansion_budget"] == question.grammar.expansion_budget
