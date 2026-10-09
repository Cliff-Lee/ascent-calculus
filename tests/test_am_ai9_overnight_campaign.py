"""Offline checks for resumable AI-guided overnight search campaigns."""

import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ac.ai import AIRequestCancelledError
from ac.discovery.dossiers import build_research_dossier, validate_dossier
from ac.discovery.experiment_refinement import EXPERIMENT_REFINEMENT_JSON_SCHEMA
from ac.discovery.jobs import ResearchJobStore
from ac.discovery.overnight_campaign import (
    CampaignBudgetReached,
    MAX_REFINEMENTS,
    MAX_TOTAL_CANDIDATES,
    OVERNIGHT_HANDLER_ID,
    run_overnight_campaign,
    validate_overnight_options,
)
from ac.discovery.worker import PauseRequested
from ac.gui.discovery_campaign import build_transformation_family_spec


def _root_spec(candidate_budget=2):
    return build_transformation_family_spec(
        source_family="modified",
        target_family="revised",
        rule_mode="avoid",
        source_patterns="111,2122",
        target_patterns="111",
        offsets="0:0,0:+2",
        start=1,
        stop=3,
        max_cost=3,
        max_steps=2,
        candidate_budget=candidate_budget,
    )


def _failure_result(spec, *, candidates_tested=2):
    scenario = spec.scenarios[0]
    failure = {
        "kind": "outside_target",
        "base_degree": max(1, scenario.degrees.start),
        "source_degree": max(1, scenario.degrees.start + scenario.source_offset),
        "target_degree": max(1, scenario.degrees.start + scenario.target_offset),
        "source": {"values": [1, 1], "height": 1},
        "other_source": None,
        "output": {"values": [1, 2, 2], "height": 2},
        "detail": "Exact deterministic test failure.",
    }
    candidate = {
        "program": "PrefixLift(1)",
        "cost": 1,
        "scenario_count": len(spec.scenarios),
        "matching_scenario_count": 0,
        "bijection_on_every_scenario": False,
        "scenario_results": [{
            "scenario_index": 0,
            "specification_fingerprint": scenario.fingerprint,
            "source_class": scenario.source.describe(),
            "target_class": scenario.target.describe(),
            "source_offset": scenario.source_offset,
            "target_offset": scenario.target_offset,
            "degree_shift": scenario.degree_shift,
            "finite_match": False,
            "verified_through": scenario.degrees.stop,
            "evaluation": {"first_failure": failure},
        }],
    }
    return {
        "specification_fingerprint": spec.fingerprint,
        "scenario_count": len(spec.scenarios),
        "candidates_tested": candidates_tested,
        "candidate_budget": spec.candidate_budget,
        "effective_candidate_budget": spec.candidate_budget,
        "exact_candidates": [],
        "ranked_candidates": [candidate],
        "proof_status": "not_proved",
        "proof_obligations": ["prove the proposed map for all degrees"],
    }


def _design_response(degree_stop=4):
    return {
        "design": {
            "status": "plan",
            "scope_note": "Retain the class grid and extend the finite interval.",
            "title": "Extend the offset comparison",
            "research_interpretation": "Check whether the observed behavior persists one more degree.",
            "assumptions": ["The failure is finite evidence only."],
            "experiment": {
                "source_family": "modified",
                "target_family": "revised",
                "rule_mode": "avoid",
                "source_patterns": ["111", "2122"],
                "target_patterns": ["111"],
                "offset_pairs": [{"source": 0, "target": 0}, {"source": 0, "target": 2}],
                "degree_start": 1,
                "degree_stop": degree_stop,
                "max_cost": 3,
                "max_steps": 2,
                "candidate_budget": 100,
            },
        },
        "counterexample_analysis": {
            "referenced_scenario_indices": [0],
            "evidence_interpretation": "The first listed scenario records an exact target-membership failure.",
            "proposed_change": "Extend the tested base-degree interval.",
        },
    }


def _options(**overrides):
    raw = {
        "endpoint": "http://localhost:11434",
        "model": "qwen3.5:9b",
        "timeout_seconds": 30,
        "model_locality": "local",
        "max_refinements": 1,
        "max_total_candidates": 20,
        "max_wall_seconds": 3600,
    }
    raw.update(overrides)
    return raw


class _Context:
    def __init__(self, *, pause_on_ai_response=False):
        self.store = SimpleNamespace(path=Path("/tmp/overnight-test.sqlite3"))
        self.checkpoint_state = {}
        self.progress = {}
        self.pause_on_ai_response = pause_on_ai_response

    def checkpoint(self, state, progress=None):
        self.checkpoint_state = json.loads(json.dumps(state))
        self.progress = dict(progress or {})
        if self.pause_on_ai_response and state.get("pending_ai_response") is not None:
            raise PauseRequested

    def check_control(self):
        return None


class AMAI9OvernightCampaignTests(unittest.TestCase):
    def test_options_are_strictly_bounded_and_loopback_only(self):
        options = validate_overnight_options(_options())
        self.assertEqual(options["model_locality"], "local")
        self.assertEqual(options["max_refinements"], 1)
        self.assertEqual(EXPERIMENT_REFINEMENT_JSON_SCHEMA["additionalProperties"], False)
        for bad in (
            _options(max_refinements=MAX_REFINEMENTS + 1),
            _options(max_total_candidates=MAX_TOTAL_CANDIDATES + 1),
            _options(max_wall_seconds=59),
            _options(endpoint="http://example.org:11434"),
            {**_options(), "api_key": "must not be accepted"},
        ):
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                validate_overnight_options(bad)

    def test_search_ai_refinement_and_follow_up_are_saved_as_finite_evidence(self):
        spec = _root_spec()
        options = _options()
        job = SimpleNamespace(id="overnighttest", question=spec, options=options, checkpoint={})
        context = _Context()
        calls = []
        response = _design_response()

        def fake_search(child_job, _context):
            calls.append(child_job.question)
            return _failure_result(child_job.question)

        class FakeAIService:
            def __init__(self, _provider):
                pass

            def chat(self, request, cancellation=None):
                self_request.append(request)
                return SimpleNamespace(text=json.dumps(response), structured_data=response, model="qwen3.5:9b")

        self_request = []
        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=fake_search), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", return_value=object()), \
             patch("ac.discovery.overnight_campaign.AIService", FakeAIService):
            result = run_overnight_campaign(job, context)

        report = result["overnight_campaign"]
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0].fingerprint, calls[1].fingerprint)
        self.assertEqual(report["stop_reason"], "refinement_budget")
        self.assertEqual(result["proof_status"], "not_proved")
        self.assertEqual(result["candidates_tested"], 4)
        self.assertEqual(len(report["completed_rounds"]), 2)
        self.assertEqual(len(report["assistant_iterations"]), 1)
        iteration = report["assistant_iterations"][0]
        self.assertIn("Exact parent specification", iteration["user_prompt"])
        self.assertEqual(iteration["validation_status"], "validated_bounded_experiment")
        self.assertEqual(iteration["verification_status"].split(";")[0], "unverified AI proposal")
        self.assertEqual(iteration["applied_specification_fingerprint"], calls[1].fingerprint)
        self.assertLessEqual(calls[1].candidate_budget, options["max_total_candidates"] - 2)
        self.assertEqual(calls[1].grammar.candidate_budget, calls[1].candidate_budget)
        self.assertEqual(len(self_request), 1)

    def test_invalid_ai_failure_reference_stops_before_a_follow_up_search(self):
        spec = _root_spec()
        job = SimpleNamespace(id="overnightreject", question=spec, options=_options(), checkpoint={})
        context = _Context()
        invalid = _design_response()
        invalid["counterexample_analysis"]["referenced_scenario_indices"] = [99]
        search_calls = []

        class FakeAIService:
            def __init__(self, _provider):
                pass

            def chat(self, _request, cancellation=None):
                return SimpleNamespace(text=json.dumps(invalid), structured_data=invalid, model="qwen3.5:9b")

        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=lambda child, _ctx: (search_calls.append(child.question) or _failure_result(child.question))), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", return_value=object()), \
             patch("ac.discovery.overnight_campaign.AIService", FakeAIService):
            result = run_overnight_campaign(job, context)
        report = result["overnight_campaign"]
        self.assertEqual(len(search_calls), 1)
        self.assertEqual(report["stop_reason"], "proposal_rejected")
        self.assertEqual(report["assistant_iterations"][0]["validation_status"], "rejected")
        self.assertNotIn("applied_specification", report["assistant_iterations"][0])
        self.assertEqual(result["proof_status"], "not_proved")

    def test_exact_finite_match_stops_before_requesting_ai(self):
        spec = _root_spec()
        job = SimpleNamespace(id="overnightexact", question=spec, options=_options(), checkpoint={})
        exact = _failure_result(spec)
        exact["exact_candidates"] = [exact["ranked_candidates"][0]]
        exact["exact_candidates"][0]["bijection_on_every_scenario"] = True

        with patch("ac.discovery.overnight_campaign.run_worker_search", return_value=exact), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", side_effect=AssertionError("AI must not run after a full finite match")):
            result = run_overnight_campaign(job, _Context())
        self.assertEqual(result["overnight_campaign"]["stop_reason"], "finite_match_found")
        self.assertEqual(len(result["overnight_campaign"]["completed_rounds"]), 1)
        self.assertEqual(result["proof_status"], "not_proved")

    def test_persisted_ai_response_is_reused_after_pause_without_another_request(self):
        spec = _root_spec()
        options = _options()
        context = _Context(pause_on_ai_response=True)
        job = SimpleNamespace(id="overnightresume", question=spec, options=options, checkpoint={})
        response = _design_response()

        class FakeAIService:
            def __init__(self, _provider):
                pass

            def chat(self, _request, cancellation=None):
                return SimpleNamespace(text=json.dumps(response), structured_data=response, model="qwen3.5:9b")

        fake_search = lambda child_job, _ctx: _failure_result(child_job.question)
        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=fake_search), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", return_value=object()), \
             patch("ac.discovery.overnight_campaign.AIService", FakeAIService):
            with self.assertRaises(PauseRequested):
                run_overnight_campaign(job, context)

        saved = context.checkpoint_state
        self.assertIsNotNone(saved["pending_ai_response"])
        self.assertTrue(saved["pending_ai_request"])
        resumed_job = SimpleNamespace(
            id=job.id, question=spec, options=options, checkpoint=saved,
        )
        calls = []
        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=lambda child, ctx: (calls.append(child.question) or _failure_result(child.question))), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", return_value=object()), \
             patch("ac.discovery.overnight_campaign.AIService", side_effect=AssertionError("stored response should be reused")):
            result = run_overnight_campaign(resumed_job, _Context())
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["overnight_campaign"]["stop_reason"], "refinement_budget")
        self.assertEqual(len(result["overnight_campaign"]["assistant_iterations"]), 1)

    def test_pause_during_ai_request_cancels_provider_and_keeps_request_checkpoint(self):
        spec = _root_spec()
        job = SimpleNamespace(id="overnightpause", question=spec, options=_options(), checkpoint={})
        calls = {"controls": 0}

        class PausingContext(_Context):
            def check_control(self):
                calls["controls"] += 1
                if calls["controls"] >= 2:
                    raise PauseRequested

        class WaitingAIService:
            def __init__(self, _provider):
                pass

            def chat(self, _request, cancellation=None):
                while not cancellation.cancelled:
                    time.sleep(0.01)
                raise AIRequestCancelledError("AI request cancelled.")

        context = PausingContext()
        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=lambda child, ctx: _failure_result(child.question)), \
             patch("ac.discovery.overnight_campaign._memory_record"), \
             patch("ac.discovery.overnight_campaign.OllamaProvider", return_value=object()), \
             patch("ac.discovery.overnight_campaign.AIService", WaitingAIService):
            with self.assertRaises(PauseRequested):
                run_overnight_campaign(job, context)
        self.assertEqual(context.checkpoint_state["stage"], "awaiting_ai_refinement")
        self.assertTrue(context.checkpoint_state["pending_ai_request"])

    def test_elapsed_budget_report_retains_partial_search_checkpoint(self):
        spec = _root_spec()
        job = SimpleNamespace(id="overnightbudget", question=spec, options=_options(), checkpoint={})
        context = _Context()

        def budgeted_search(_child_job, nested_context):
            nested_context.checkpoint({"family_search_version": 1, "examined": 1, "ranked_candidates": []}, {})
            raise CampaignBudgetReached

        with patch("ac.discovery.overnight_campaign.run_worker_search", side_effect=budgeted_search), \
             patch("ac.discovery.overnight_campaign._memory_record"):
            result = run_overnight_campaign(job, context)
        campaign = result["overnight_campaign"]
        self.assertEqual(campaign["stop_reason"], "elapsed_time_budget")
        self.assertEqual(result["candidates_tested"], 1)
        self.assertEqual(result["round_count"], 0)
        self.assertEqual(campaign["active_round"]["checkpoint"]["examined"], 1)
        self.assertEqual(result["proof_status"], "not_proved")

    def test_dossier_indexes_each_exact_follow_up_specification(self):
        root = _root_spec()
        follow_up = build_transformation_family_spec(
            source_family="modified", target_family="revised", rule_mode="avoid",
            source_patterns="111,2122", target_patterns="111", offsets="0:0,0:+2",
            start=1, stop=4, max_cost=3, max_steps=2, candidate_budget=8,
        )
        options = _options()
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchJobStore(Path(directory) / "research.sqlite3")
            created = store.create_job(root, handler=OVERNIGHT_HANDLER_ID, options=options)
            claimed = store.claim_next("test-worker")
            result = {
                "status": "bounded_overnight_campaign",
                "proof_status": "not_proved",
                "interpretation": "Finite evidence only.",
                "candidates_tested": 7,
                "effective_candidate_budget": options["max_total_candidates"],
                "overnight_campaign": {
                    "version": 1,
                    "root_specification": root.to_dict(),
                    "root_specification_fingerprint": root.fingerprint,
                    "stop_reason": "refinement_budget",
                    "completed_rounds": [
                        {"round_index": 0, "specification": root.to_dict(), "specification_fingerprint": root.fingerprint,
                         "candidates_tested": 3, "search_result": {"specification_fingerprint": root.fingerprint, "candidates_tested": 3, "effective_candidate_budget": 2, "proof_status": "not_proved"}},
                        {"round_index": 1, "specification": follow_up.to_dict(), "specification_fingerprint": follow_up.fingerprint,
                         "candidates_tested": 4, "search_result": {"specification_fingerprint": follow_up.fingerprint, "candidates_tested": 4, "effective_candidate_budget": 8, "proof_status": "not_proved"}},
                    ],
                    "assistant_iterations": [{"user_prompt": "Exact finite failure evidence", "response_text": "{}", "verification_status": "unverified"}],
                },
            }
            self.assertEqual(claimed.id, created.id)
            store.finish(created.id, "test-worker", result)
            saved = store.get_job(created.id)
            dossier = build_research_dossier(saved)
        checked = validate_dossier(dossier)
        rounds = checked["tested_bounds"]["overnight_rounds"]
        self.assertEqual([item["specification_fingerprint"] for item in rounds], [root.fingerprint, follow_up.fingerprint])
        self.assertEqual([item["candidates_tested"] for item in rounds], [3, 4])
        self.assertEqual(checked["finite_result"]["overnight_campaign"]["assistant_iterations"][0]["response_text"], "{}")
        self.assertEqual(checked["execution"]["options"], options)
        self.assertEqual(checked["proof_status"], "not_proved")
        tampered = json.loads(json.dumps(checked))
        tampered["tested_bounds"]["overnight_rounds"][1]["specification"]["candidate_budget"] = 999
        with self.assertRaisesRegex(ValueError, "index"):
            validate_dossier(tampered)


if __name__ == "__main__":
    unittest.main()
