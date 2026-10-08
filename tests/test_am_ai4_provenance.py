from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from ac.ai import create_assistant_review
from ac.discovery.dossiers import build_research_dossier, validate_dossier
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.transformation_search import TransformationGrammarSpec, TransformationSearchSpec
from ac.discovery.specification import ClassSpec, DegreeWindow


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


def _review():
    evidence = {"evidence_status": "finite computation; not a proof", "candidate": {"program": "Identity()"}}
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
    messages = (
        {"role": "system", "content": "Explain finite evidence; do not claim proof."},
        {"role": "user", "content": f"Question: summarize\n\nExact bounded search record:\n{encoded}"},
    )
    return create_assistant_review(
        provider_id="ollama-loopback",
        provider_name="Ollama API (loopback)",
        endpoint="http://localhost:11434",
        requested_model="qwen3.5:9b",
        response_model="qwen3.5:9b",
        evidence=evidence,
        messages=messages,
        parameters={"temperature": 0.2, "max_tokens": 1200, "timeout_seconds": 240, "output_mode": "text"},
        response_text="The computations match through the stated bound; this is not a proof.",
        inference_locality="local",
        requested_at="2026-10-08T10:00:00+00:00",
        completed_at="2026-10-08T10:00:03+00:00",
    )


class AMAI4ProvenanceTests(unittest.TestCase):
    def test_assistant_review_persists_and_round_trips_in_dossier_without_changing_math_result(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "jobs.sqlite3"
            store = ResearchJobStore(database)
            job = store.create_job(_question(), handler="search-transformations")
            result = {"status": "finite_transformation_search", "proof_status": "not_proved", "exact_candidates": []}
            review = _review()
            self.assertEqual(store.record_assistant_review(job.id, review), review)
            self.assertEqual(store.record_assistant_review(job.id, review), review)

            restored_reviews = ResearchJobStore(database).assistant_reviews(job.id)
            dossier = build_research_dossier(
                replace(job, result=result),
                assistant_reviews=restored_reviews,
            )

        self.assertEqual(len(restored_reviews), 1)
        self.assertEqual(dossier["version"], 3)
        self.assertEqual(dossier["assistant_reviews"], [review])
        self.assertEqual(dossier["finite_result"], result)
        self.assertEqual(dossier["proof_status"], "not_proved")
        self.assertEqual(validate_dossier(dossier), dossier)

    def test_older_dossiers_remain_readable_and_v3_rejects_tampered_ai_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            job = ResearchJobStore(Path(directory) / "jobs.sqlite3").create_job(
                _question(), handler="search-transformations"
            )
        dossier = build_research_dossier(job, assistant_reviews=[_review()])

        legacy = deepcopy(dossier)
        legacy.pop("assistant_reviews")
        legacy.pop("research_priority_review")
        legacy["version"] = 1
        self.assertEqual(validate_dossier(legacy), legacy)

        version_two = deepcopy(dossier)
        version_two.pop("research_priority_review")
        version_two["version"] = 2
        self.assertEqual(validate_dossier(version_two), version_two)

        changed = deepcopy(dossier)
        changed["assistant_reviews"][0]["response"]["verification_status"] = "proved"
        with self.assertRaisesRegex(ValueError, "explicitly unverified"):
            validate_dossier(changed)

        changed = deepcopy(dossier)
        changed["assistant_reviews"][0]["request"]["messages"][1]["content"] += " changed"
        with self.assertRaisesRegex(ValueError, "request fingerprint"):
            validate_dossier(changed)


if __name__ == "__main__":
    import unittest
    unittest.main()
