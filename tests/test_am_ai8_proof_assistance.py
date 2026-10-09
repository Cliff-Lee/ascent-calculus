"""Offline checks for AM-AI8's structured and explicitly unverified proof plans."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from ac.ai import create_assistant_review
from ac.discovery.dossiers import build_research_dossier, validate_dossier
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.proof_assistance import (
    PROOF_PLAN_JSON_SCHEMA,
    build_proof_assistance_context,
    parse_proof_plan_json,
    render_proof_plan,
    validate_proof_assistance_context,
    validate_proof_plan,
)
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import TransformationGrammarSpec, TransformationSearchSpec


def _context():
    evidence = {
        "evidence_status": "finite computation; not a proof",
        "research_question": {"degree_window": {"start": 2, "stop": 5}},
        "candidate": {
            "program": "PrefixLift(2)",
            "matching_scenario_count": 1,
            "scenario_count": 1,
            "scenario_results": [{"scenario_index": 0, "finite_match": True, "verified_through": 5}],
        },
    }
    return build_proof_assistance_context(evidence, ["Prove target preservation", "Prove a two-sided inverse"])


def _raw(context=None):
    context = context or _context()
    return {
        "context_fingerprint": context["context_fingerprint"],
        "title": "A proof route for PrefixLift",
        "goal": "Establish a bijection for every object in the stated source family.",
        "steps": [
            {
                "id": "S1",
                "role": "candidate_lemma",
                "statement": "PrefixLift preserves membership in the target class.",
                "strategy": "Track the newly inserted prefix and check its adjacent rises against the class definition.",
                "obligation_refs": ["O1"],
                "depends_on": [],
            },
            {
                "id": "S2",
                "role": "inverse_formula",
                "statement": "Deleting the inserted prefix recovers the source word.",
                "strategy": "Give the deletion rule and prove both compositions are identity maps.",
                "obligation_refs": ["O2"],
                "depends_on": ["S1"],
            },
        ],
        "unresolved_gaps": ["The deletion rule must be shown to stay within the source family."],
        "useful_checks": ["Search for a small-degree counterexample to the proposed deletion rule."],
    }


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


class AMAI8ProofAssistanceTests(unittest.TestCase):
    def test_plan_is_labeled_unverified_and_only_structural_integrity_is_checked(self):
        context = _context()
        plan = validate_proof_plan(_raw(context), context)
        rendered = render_proof_plan(plan)
        self.assertIn("AI-PROPOSED · UNVERIFIED", rendered)
        self.assertIn("Researcher status · proposed, not verified", rendered)
        self.assertIn("inverse formula", rendered)
        self.assertIn("O1", rendered)
        self.assertEqual(plan.context_fingerprint, context["context_fingerprint"])
        self.assertEqual(PROOF_PLAN_JSON_SCHEMA["additionalProperties"], False)

    def test_unknown_or_missing_obligations_bad_context_and_cycles_are_rejected(self):
        context = _context()
        unknown = _raw(context)
        unknown["steps"][0]["obligation_refs"] = ["O9"]
        with self.assertRaisesRegex(ValueError, "not supplied"):
            validate_proof_plan(unknown, context)

        missing = _raw(context)
        missing["steps"].pop()
        with self.assertRaisesRegex(ValueError, "every supplied obligation"):
            validate_proof_plan(missing, context)

        cyclic = _raw(context)
        cyclic["steps"][0]["depends_on"] = ["S2"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_proof_plan(cyclic, context)

        tampered = deepcopy(context)
        tampered["candidate_evidence"]["candidate"]["verified_through"] = 99
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_proof_assistance_context(tampered)

        false_status = _raw(context)
        false_status["proof_status"] = "proved"
        with self.assertRaisesRegex(ValueError, "fields do not match"):
            validate_proof_plan(false_status, context)

    def test_obligations_are_deduplicated_and_context_must_be_finite_unproved_evidence(self):
        evidence = {"evidence_status": "finite computation; not a proof", "candidate": {"program": "Id"}}
        context = build_proof_assistance_context(evidence, ["Prove P", "Prove P", "Prove Q"])
        self.assertEqual([item["id"] for item in context["proof_obligations"]], ["O1", "O2"])
        with self.assertRaisesRegex(ValueError, "finite, unproved"):
            build_proof_assistance_context({"evidence_status": "proved"}, [])

    def test_json_plan_persists_as_unverified_ai_review_in_reproducible_dossier(self):
        context = _context()
        plan_data = _raw(context)
        plan = parse_proof_plan_json(json.dumps(plan_data), context)
        response_text = json.dumps(plan_data, ensure_ascii=False, sort_keys=True)
        evidence_text = json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True)
        messages = [
            {"role": "system", "content": "Return exact schema JSON. This is an unverified proof plan."},
            {"role": "user", "content": f"Proof obligations and candidate evidence:\n{evidence_text}"},
        ]
        self.assertIn(evidence_text, messages[1]["content"])

        review = create_assistant_review(
            provider_id="ollama-loopback",
            provider_name="Ollama API (loopback)",
            endpoint="http://localhost:11434",
            requested_model="qwen3.5:9b",
            response_model="qwen3.5:9b",
            evidence=context,
            messages=messages,
            parameters={"temperature": 0.2, "max_tokens": 2800, "timeout_seconds": 240, "output_mode": "json"},
            response_text=response_text,
            inference_locality="local",
            requested_at="2026-10-08T10:00:00+00:00",
            completed_at="2026-10-08T10:00:02+00:00",
        )
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchJobStore(Path(directory) / "research.sqlite3")
            job = store.create_job(_question(), handler="search-transformations")
            store.record_assistant_review(job.id, review)
            saved = store.assistant_reviews(job.id)
            dossier = build_research_dossier(job, assistant_reviews=saved)
        self.assertEqual(plan.title, "A proof route for PrefixLift")
        self.assertEqual(dossier["proof_status"], "not_proved")
        self.assertEqual(dossier["assistant_reviews"][0]["response"]["verification_status"], "unverified")
        self.assertEqual(validate_dossier(dossier), dossier)


if __name__ == "__main__":
    unittest.main()
