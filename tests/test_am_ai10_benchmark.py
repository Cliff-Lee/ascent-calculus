"""AM-AI10a paired benchmark and offline isolation tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ac.gui.discovery_campaign import build_transformation_family_spec
from experiments.am_ai10_benchmark import (
    _candidate_scenario_pairs,
    load_family_spec,
    run_benchmark,
)


def _spec():
    return build_transformation_family_spec(
        source_family="ordinary",
        target_family="modified",
        rule_mode="avoid",
        source_patterns="*",
        target_patterns="*",
        offsets="0:0,0:+1",
        start=1,
        stop=2,
        max_cost=1,
        max_steps=1,
        candidate_budget=8,
        expansion_budget=200,
    )


class AMAI10BenchmarkTests(unittest.TestCase):
    def test_spec_loader_accepts_exact_family_spec_and_dossier_shape(self):
        spec = _spec()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "question.json"
            path.write_text(json.dumps(spec.to_dict()), encoding="utf-8")
            self.assertEqual(load_family_spec(path).fingerprint, spec.fingerprint)
            path.write_text(json.dumps({
                "mathematical_question": {"specification": spec.to_dict()},
            }), encoding="utf-8")
            self.assertEqual(load_family_spec(path).fingerprint, spec.fingerprint)
            path.write_text(json.dumps({
                "overnight_campaign": {"root_specification": spec.to_dict()},
            }), encoding="utf-8")
            self.assertEqual(load_family_spec(path).fingerprint, spec.fingerprint)

    def test_offline_baseline_never_constructs_an_ai_provider(self):
        spec = _spec()
        with patch(
            "ac.discovery.overnight_campaign.OllamaProvider",
            side_effect=AssertionError("offline baseline must not instantiate Ollama"),
        ):
            record = run_benchmark(spec, candidate_budget=8, with_ai=False)

        self.assertEqual(record["classification"], "offline_deterministic_baseline")
        self.assertEqual(record["proof_status"], "not_proved")
        self.assertEqual(record["question"]["root_specification_fingerprint"], spec.fingerprint)
        self.assertIsNone(record["ai_guided"])
        self.assertIsNone(record["comparison"])
        self.assertLessEqual(record["deterministic_baseline"]["candidates_tested"], 8)

    def test_ai_guided_option_requires_an_explicit_model_and_shared_cap_is_reported(self):
        with self.assertRaisesRegex(ValueError, "explicit Ollama model"):
            run_benchmark(_spec(), with_ai=True)

        record = run_benchmark(_spec(), candidate_budget=3, with_ai=False)
        self.assertEqual(record["budget"]["effective_total_candidate_cap"], 3)
        self.assertFalse(record["budget"]["baseline_budget_expanded_above_root_spec"])

    def test_exact_match_pairs_are_bound_to_the_scenario_fingerprints(self):
        spec = _spec()
        scenario = spec.scenarios[0]
        fingerprint = scenario.fingerprint
        result = {
            "exact_candidates": [{
                "program": "Identity()",
                "scenario_results": [{
                    "specification_fingerprint": fingerprint,
                    "finite_match": True,
                }],
            }],
        }
        pairs_at_root_budget = _candidate_scenario_pairs(result, spec.to_dict())
        larger_budget = spec.candidate_budget + 4
        grammar = replace(spec.grammar, candidate_budget=larger_budget)
        larger_spec = replace(
            spec,
            scenarios=tuple(replace(item, grammar=grammar) for item in spec.scenarios),
            candidate_budget=larger_budget,
        )
        result["exact_candidates"][0]["scenario_results"][0]["specification_fingerprint"] = (
            larger_spec.scenarios[0].fingerprint
        )
        pairs_at_larger_budget = _candidate_scenario_pairs(result, larger_spec.to_dict())
        self.assertEqual(pairs_at_root_budget, pairs_at_larger_budget)
        self.assertEqual(len(pairs_at_root_budget), 1)
        self.assertEqual(next(iter(pairs_at_root_budget))[0], "Identity()")

    def test_paired_record_uses_one_root_and_reports_guided_only_finite_matches(self):
        spec = _spec()
        first_scenario = spec.scenarios[0].fingerprint
        guided_report = {
            "candidates_tested": 3,
            "effective_candidate_budget": 12,
            "overnight_campaign": {
                "root_specification_fingerprint": spec.fingerprint,
                "round_count": 2,
                "stop_reason": "candidate_budget",
                "assistant_iterations": [{"validation_status": "validated_bounded_experiment"}],
                "completed_rounds": [{
                    "specification": spec.to_dict(),
                    "search_result": {"exact_candidates": [{
                        "program": "PrefixLift(1)",
                        "scenario_results": [{
                            "specification_fingerprint": first_scenario,
                            "finite_match": True,
                        }],
                    }]},
                }],
            },
        }
        baseline = {"candidates_tested": 2, "exact_candidates": []}
        with patch("experiments.am_ai10_benchmark.run_worker_search", return_value=baseline), \
             patch("experiments.am_ai10_benchmark.run_overnight_campaign", return_value=guided_report) as guided:
            record = run_benchmark(
                spec,
                candidate_budget=12,
                with_ai=True,
                model="local-test-model",
                model_locality="remote",
            )

        self.assertEqual(guided.call_args.args[0].question.fingerprint, spec.fingerprint)
        self.assertEqual(guided.call_args.args[0].options["max_total_candidates"], 12)
        self.assertTrue(record["comparison"]["same_root_specification"])
        self.assertTrue(record["comparison"]["same_total_candidate_cap"])
        self.assertEqual(record["deterministic_baseline"]["specification"]["candidate_budget"], 12)
        self.assertTrue(record["budget"]["baseline_budget_expanded_above_root_spec"])
        self.assertEqual(record["comparison"]["additional_pair_count"], 1)
        self.assertEqual(record["ai_guided"]["declared_inference_locality"], "remote")
        self.assertEqual(record["ai_guided"]["validated_follow_up_count"], 1)

    def test_loader_rejects_non_family_searches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"format": "unknown"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "transformation-family"):
                load_family_spec(path)


if __name__ == "__main__":
    unittest.main()
