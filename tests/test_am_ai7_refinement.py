"""Offline tests for counterexample-guided bounded experiment refinement."""

import json
from pathlib import Path
import tempfile
import unittest

from ac.discovery.dossiers import build_research_dossier
from ac.discovery.experiment_design import validate_experiment_design
from ac.discovery.experiment_refinement import (
    build_experiment_refinement_options,
    build_refinement_context,
    validate_experiment_refinement,
    validate_refinement_context,
)
from ac.discovery.jobs import ResearchJobStore


def _design_response():
    return {
        "status": "plan",
        "scope_note": "Extend only the tested degree window while retaining the class and offset grid.",
        "title": "Continue the modified-to-revised comparison",
        "research_interpretation": "Check whether the observed failure is isolated to the tested finite range.",
        "assumptions": ["The finite failure is a reason to test a larger range, not evidence for a repair."],
        "experiment": {
            "source_family": "modified",
            "target_family": "revised",
            "rule_mode": "avoid",
            "source_patterns": ["111", "2122"],
            "target_patterns": ["111"],
            "offset_pairs": [{"source": 0, "target": 0}, {"source": 0, "target": 2}],
            "degree_start": 2,
            "degree_stop": 6,
            "max_cost": 4,
            "max_steps": 2,
            "candidate_budget": 100,
        },
    }


def _response():
    return {
        "design": _design_response(),
        "counterexample_analysis": {
            "referenced_scenario_indices": [1],
            "evidence_interpretation": "Scenario 1 first failed at base degree 4 with a source outside the target.",
            "proposed_change": "Retain the same class and offset comparisons and extend the upper degree by one.",
        },
    }


def _parent():
    raw = _design_response()
    raw["experiment"]["degree_stop"] = 5
    design = validate_experiment_design(raw)
    scenario = design.spec.scenarios[1]
    failure = {
        "kind": "outside_target",
        "base_degree": 4,
        "source_degree": 4,
        "target_degree": 6,
        "source": {"values": [0, 1, 1, 2], "height": 2},
        "other_source": None,
        "output": {"values": [0, 1, 2, 2, 3, 3], "height": 3},
        "detail": "The transformed word failed exact target membership.",
    }
    candidate = {
        "program": "PrefixLift(2) ∘ BlockRecipe(ascending)",
        "cost": 5,
        "scenario_count": 4,
        "matching_scenario_count": 3,
        "scenario_results": [
            {
                "scenario_index": 1,
                "specification_fingerprint": scenario.fingerprint,
                "source_class": scenario.source.describe(),
                "target_class": scenario.target.describe(),
                "source_offset": scenario.source_offset,
                "target_offset": scenario.target_offset,
                "verified_through": 5,
                "finite_match": False,
                "evaluation": {"first_failure": failure},
            },
        ],
    }
    context = build_refinement_context(
        parent_job_id="parent123",
        prior_specification=design.spec.to_dict(),
        prior_specification_fingerprint=design.spec.fingerprint,
        candidate=candidate,
    )
    return design, candidate, context


class AMAI7RefinementTests(unittest.TestCase):
    def test_context_carries_exact_engine_witness_and_stable_lineage_hashes(self):
        _design, _candidate, context = _parent()
        checked = validate_refinement_context(context)
        witness = checked["candidate"]["failure_evidence"][0]
        self.assertEqual(witness["scenario_index"], 1)
        self.assertEqual(witness["failure"]["source"]["values"], [0, 1, 1, 2])
        self.assertEqual(witness["failure"]["output"]["values"], [0, 1, 2, 2, 3, 3])
        self.assertEqual(len(checked["counterexample_evidence_fingerprint"]), 64)

    def test_response_must_cite_supplied_failure_indices_and_change_the_spec(self):
        _design, _candidate, context = _parent()
        parsed = validate_experiment_refinement(_response(), context)
        self.assertEqual(parsed.referenced_scenario_indices, (1,))
        self.assertEqual(parsed.design.spec.fingerprint != context["prior_specification_fingerprint"], True)

        unknown = _response()
        unknown["counterexample_analysis"]["referenced_scenario_indices"] = [9]
        with self.assertRaisesRegex(ValueError, "no supplied engine failure"):
            validate_experiment_refinement(unknown, context)

        duplicate = _response()
        duplicate["counterexample_analysis"]["referenced_scenario_indices"] = [1, 1]
        with self.assertRaisesRegex(ValueError, "distinct integers"):
            validate_experiment_refinement(duplicate, context)

    def test_unchanged_design_and_tampered_witness_are_rejected(self):
        _design, _candidate, context = _parent()
        unchanged = _response()
        unchanged["design"]["experiment"]["degree_stop"] = 5
        with self.assertRaisesRegex(ValueError, "unchanged"):
            validate_experiment_refinement(unchanged, context)

        tampered = json.loads(json.dumps(context))
        tampered["candidate"]["failure_evidence"][0]["failure"]["base_degree"] = 99
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_refinement_context(tampered)

    def test_refinement_lineage_is_saved_in_job_dossier_and_marks_edits(self):
        _parent_design, _candidate, context = _parent()
        raw_response = _response()
        refinement = validate_experiment_refinement(raw_response, context)
        design = refinement.design
        provenance = {
            "question": "Use the recorded failure to suggest the most informative follow-up.",
            "endpoint": "http://localhost:11434",
            "requested_model": "qwen3.5:9b",
            "response_model": "qwen3.5:9b",
            "provider_id": "ollama-loopback",
            "inference_locality": "local",
            "requested_at": "2026-10-08T10:00:00+00:00",
            "completed_at": "2026-10-08T10:00:02+00:00",
            "system_prompt": "Use exact finite failures; do not claim proof.",
            "user_prompt": json.dumps(context, sort_keys=True),
            "response_text": json.dumps(raw_response),
            "parameters": {"temperature": 0.1, "max_tokens": 1800, "output_mode": "json"},
        }
        edited = "a" * 64
        options = build_experiment_refinement_options(
            design=design,
            provenance=provenance,
            context=context,
            refinement=refinement,
            applied_spec_fingerprint=edited,
        )
        record = options["experiment_refinement"]
        self.assertEqual(record["parent_job_id"], "parent123")
        self.assertEqual(record["parent_specification_fingerprint"], context["prior_specification_fingerprint"])
        self.assertEqual(record["counterexample_evidence_fingerprint"], context["counterexample_evidence_fingerprint"])
        self.assertEqual(record["application_status"], "edited_after_proposal")
        self.assertEqual(record["verification_status"], "unverified follow-up proposal; exact finite engine failures supplied; follow-up not run")

        with tempfile.TemporaryDirectory() as directory:
            store = ResearchJobStore(Path(directory) / "research.sqlite3")
            job = store.create_job(design.spec, handler="search-transformation-families", options=options)
            dossier = build_research_dossier(store.get_job(job.id))
        saved = dossier["execution"]["options"]["experiment_refinement"]
        self.assertEqual(saved["parent_context"], context)
        self.assertEqual(saved["referenced_scenario_indices"], [1])
        self.assertEqual(saved["application_status"], "edited_after_proposal")


if __name__ == "__main__":
    unittest.main()
