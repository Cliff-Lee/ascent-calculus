import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace

from ac.discovery.dossiers import build_research_dossier, validate_dossier
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.significance import build_research_priority_review
from ac.discovery.transformation_family import TransformationFamilySearchSpec
from ac.discovery.transformation_search import TransformationGrammarSpec


def _question():
    def scenario(source, target, source_offset, target_offset):
        return SimpleNamespace(
            source=SimpleNamespace(family=source),
            target=SimpleNamespace(family=target),
            source_offset=source_offset,
            target_offset=target_offset,
            degrees=SimpleNamespace(start=1, stop=3),
        )
    return SimpleNamespace(
        scenarios=(
            scenario("modified", "revised", 0, 0),
            scenario("modified", "revised", 0, 2),
            scenario("ordinary", "revised", 0, 0),
            scenario("ordinary", "revised", 0, 2),
        ),
        grammar=SimpleNamespace(max_cost=4),
        fingerprint="a" * 64,
    )


def _candidate(program, matched, cost):
    return {
        "program": program,
        "cost": cost,
        "scenario_count": 4,
        "matching_scenario_count": len(matched),
        "bijection_on_every_scenario": len(matched) == 4,
        "scenario_results": [
            {
                "scenario_index": index,
                "finite_match": index in matched,
                "verified_through": 3,
            }
            for index in range(4)
        ],
    }


class AMAI5SignificanceTests(unittest.TestCase):
    def test_ranking_is_deterministic_and_explains_its_finite_inputs(self):
        exact = _candidate("BlockInsert()", {0, 1, 2, 3}, 4)
        partial = _candidate("SimpleSwap()", {0, 1}, 1)
        result = {
            "ranked_candidates": [partial, exact],
            "research_memory": {"candidates": [
                {"program": "BlockInsert()", "novelty": "new_transformation"},
                {"program": "SimpleSwap()", "novelty": "exact_program_duplicate"},
            ]},
        }

        first = build_research_priority_review(_question(), result)
        second = build_research_priority_review(_question(), result)
        self.assertEqual(first, second)
        self.assertEqual(first["ranked_candidates"][0]["program"], "BlockInsert()")
        exact_review = first["ranked_candidates"][0]
        partial_review = first["ranked_candidates"][1]
        self.assertEqual(exact_review["priority_score"], 85)
        self.assertEqual(exact_review["confidence_in_score_inputs"], "high")
        self.assertEqual(exact_review["components"]["family_and_offset_breadth"]["points"], 20)
        self.assertLess(partial_review["priority_score"], exact_review["priority_score"])
        self.assertTrue(any("finite check" in reason for reason in exact_review["reasons"]))
        self.assertTrue(any("not a probability" in note for note in exact_review["uncertainties"]))

    def test_missing_memory_is_explicit_and_does_not_falsely_claim_high_confidence(self):
        report = build_research_priority_review(
            _question(),
            {"ranked_candidates": [_candidate("Candidate()", {0, 1, 2, 3}, 1)]},
        )
        review = report["ranked_candidates"][0]
        self.assertEqual(review["components"]["research_memory_novelty"]["points"], None)
        self.assertEqual(review["confidence_in_score_inputs"], "medium")
        self.assertTrue(any("memory comparison" in note for note in review["uncertainties"]))

    def test_memory_novelty_is_a_distinct_rubric_signal(self):
        row = _candidate("Candidate()", {0, 1, 2, 3}, 1)
        unknown = build_research_priority_review(_question(), {"ranked_candidates": [row]})["ranked_candidates"][0]
        novel = build_research_priority_review(
            _question(),
            {"ranked_candidates": [row], "research_memory": {"candidates": [{"program": "Candidate()", "novelty": "new_application_of_known_transformation"}]}},
        )["ranked_candidates"][0]
        self.assertGreater(novel["priority_score"], unknown["priority_score"])
        self.assertEqual(novel["novelty_classification"], "new_application_of_known_transformation")

    def test_version_three_dossier_recomputes_and_protects_priority_review(self):
        grammar = TransformationGrammarSpec(
            operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
            position_bound=2, occurrence_rank=1, inserted_value_bound=1,
            max_selectors=20, max_atoms=20, max_cost=2, max_steps=1,
            candidate_budget=20, expansion_budget=200,
            enumeration_budget=100_000, class_object_budget=100_000,
            evaluation_budget=500_000,
        )
        question = TransformationFamilySearchSpec.from_grid(
            (ClassSpec("modified"),),
            (ClassSpec("revised"),),
            DegreeWindow(1, 2),
            grammar,
            offset_pairs=((0, 0), (0, 2)),
            candidate_budget=20,
            enumeration_budget=100_000,
            class_object_budget=100_000,
            evaluation_budget=500_000,
        )
        candidate = {
            "program": "Identity()",
            "cost": 0,
            "scenario_count": 2,
            "matching_scenario_count": 2,
            "bijection_on_every_scenario": True,
            "scenario_results": [
                {"scenario_index": index, "finite_match": True, "verified_through": 2}
                for index in range(2)
            ],
        }
        result = {
            "status": "finite_cross_scenario_search",
            "proof_status": "not_proved",
            "ranked_candidates": [candidate],
            "research_memory": {"candidates": [{"program": "Identity()", "novelty": "new_transformation"}]},
        }
        with tempfile.TemporaryDirectory() as directory:
            job = ResearchJobStore(Path(directory) / "jobs.sqlite3").create_job(
                question, handler="search-transformation-families"
            )
            dossier = build_research_dossier(replace(job, result=result))

        review = dossier["research_priority_review"]
        self.assertEqual(dossier["version"], 3)
        self.assertEqual(review["ranked_candidates"][0]["program"], "Identity()")
        self.assertEqual(validate_dossier(dossier), dossier)

        changed = deepcopy(dossier)
        changed["research_priority_review"]["ranked_candidates"][0]["priority_score"] -= 1
        with self.assertRaisesRegex(ValueError, "does not match its finite results"):
            validate_dossier(changed)


if __name__ == "__main__":
    unittest.main()
