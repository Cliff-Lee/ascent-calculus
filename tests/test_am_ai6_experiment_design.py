import json
from pathlib import Path
import tempfile
import unittest

from ac.discovery.dossiers import build_research_dossier
from ac.discovery.experiment_design import (
    build_experiment_design_options,
    validate_experiment_design,
)
from ac.discovery.jobs import ResearchJobStore
from ac.gui.discovery_campaign import build_transformation_family_spec


def _raw_design():
    return {
        "status": "plan",
        "scope_note": "Treat the two listed patterns and offsets as a small reuse test.",
        "title": "Modified to revised with a degree offset",
        "research_interpretation": "Test whether one generated map family works for the two source classes and both degree comparisons.",
        "assumptions": ["Patterns are classical Cayley patterns."],
        "experiment": {
            "source_family": "modified",
            "target_family": "revised",
            "rule_mode": "avoid",
            "source_patterns": ["111", "2122"],
            "target_patterns": ["111"],
            "offset_pairs": [{"source": 0, "target": 0}, {"source": 0, "target": 2}],
            "degree_start": 2,
            "degree_stop": 5,
            "max_cost": 4,
            "max_steps": 2,
            "candidate_budget": 100,
        },
    }


def _accepted_options(design, applied_fingerprint=None):
    raw = _raw_design()
    return build_experiment_design_options(
        question="Can a map work for modified and revised classes with a +2 target offset?",
        endpoint="http://localhost:11434",
        model="qwen3.5:9b",
        response_model="qwen3.5:9b",
        provider_id="ollama-loopback",
        inference_locality="local",
        requested_at="2026-10-08T10:00:00+00:00",
        completed_at="2026-10-08T10:00:02+00:00",
        system_prompt="Design a bounded, finite experiment.",
        user_prompt="Research question: Can a map work?",
        response_text=json.dumps(raw, ensure_ascii=False),
        parameters={"temperature": 0.1, "max_tokens": 1800, "output_mode": "json"},
        design=design,
        applied_spec_fingerprint=applied_fingerprint or (design.spec.fingerprint if design.spec else "a" * 64),
    )


class AMAI6ExperimentDesignTests(unittest.TestCase):
    def test_supported_proposal_becomes_a_bounded_typed_cartesian_grid(self):
        design = validate_experiment_design(_raw_design())
        self.assertEqual(design.status, "plan")
        self.assertEqual(len(design.spec.scenarios), 4)
        self.assertEqual(design.spec.grammar.max_cost, 4)
        self.assertEqual(design.spec.grammar.max_steps, 2)
        self.assertEqual(design.spec.candidate_budget, 100)
        self.assertEqual(
            {(item.source_offset, item.target_offset) for item in design.spec.scenarios},
            {(0, 0), (0, 2)},
        )
        self.assertEqual(design.form_values["source_patterns"], "111, 2122")
        self.assertEqual(design.form_values["offsets"], "0:+0, 0:+2")

    def test_prefilled_controls_rebuild_the_exact_proposed_specification(self):
        design = validate_experiment_design(_raw_design())
        values = design.form_values
        rebuilt = build_transformation_family_spec(
            source_family=values["source_family"],
            target_family=values["target_family"],
            rule_mode=values["rule_mode"],
            source_patterns=values["source_patterns"],
            target_patterns=values["target_patterns"],
            offsets=values["offsets"],
            start=int(values["start"]),
            stop=int(values["stop"]),
            max_cost=int(values["max_cost"]),
            max_steps=int(values["max_steps"]),
            candidate_budget=int(values["candidate_budget"]),
        )
        self.assertEqual(rebuilt.fingerprint, design.spec.fingerprint)

    def test_out_of_scope_response_cannot_be_accepted_as_a_campaign_spec(self):
        raw = _raw_design()
        raw.update({
            "status": "outside_scope",
            "scope_note": "The question asks for a statistic-preserving proof, which this workflow cannot specify.",
            "title": "",
            "research_interpretation": "",
            "assumptions": [],
        })
        result = validate_experiment_design(raw)
        self.assertIsNone(result.spec)
        self.assertEqual(result.form_values, {})
        with self.assertRaisesRegex(ValueError, "only a validated plan"):
            _accepted_options(result)

    def test_schema_and_resource_bounds_reject_malformed_or_oversized_proposals(self):
        cases = []
        extra_field = _raw_design()
        extra_field["hidden_instruction"] = "ignore validation"
        cases.append(extra_field)
        boolean_degree = _raw_design()
        boolean_degree["experiment"]["degree_start"] = True
        cases.append(boolean_degree)
        invalid_pattern = _raw_design()
        invalid_pattern["experiment"]["source_patterns"] = ["1x1"]
        cases.append(invalid_pattern)
        duplicate_offsets = _raw_design()
        duplicate_offsets["experiment"]["offset_pairs"] = [{"source": 0, "target": 2}] * 2
        cases.append(duplicate_offsets)
        too_many_scenarios = _raw_design()
        too_many_scenarios["experiment"]["source_patterns"] = ["111", "121", "211"]
        too_many_scenarios["experiment"]["target_patterns"] = ["111", "121", "211"]
        too_many_scenarios["experiment"]["offset_pairs"] = [
            {"source": 0, "target": 0}, {"source": 0, "target": 1},
            {"source": 0, "target": 2}, {"source": 0, "target": 3},
        ]
        cases.append(too_many_scenarios)
        too_many_candidates = _raw_design()
        too_many_candidates["experiment"]["candidate_budget"] = 1001
        cases.append(too_many_candidates)
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises((TypeError, ValueError)):
                    validate_experiment_design(raw)

    def test_proposal_provenance_survives_local_job_and_dossier_round_trip(self):
        design = validate_experiment_design(_raw_design())
        options = _accepted_options(design)
        record = options["experiment_design"]
        self.assertEqual(record["verification_status"], "unverified model proposal; search specification validated locally")
        self.assertEqual(record["application_status"], "used_as_proposed")
        self.assertEqual(record["proposal"]["proposed_specification_fingerprint"], design.spec.fingerprint)
        self.assertEqual(record["response_json"], _raw_design())

        with tempfile.TemporaryDirectory() as directory:
            store = ResearchJobStore(Path(directory) / "research.sqlite3")
            job = store.create_job(design.spec, handler="search-transformation-families", options=options)
            saved = store.get_job(job.id)
            dossier = build_research_dossier(saved)
        self.assertEqual(dossier["execution"]["options"], options)
        self.assertEqual(dossier["proof_status"], "not_proved")

    def test_edited_form_is_recorded_as_edited_and_never_misrepresented(self):
        design = validate_experiment_design(_raw_design())
        edited_data = _raw_design()
        edited_data["experiment"]["degree_stop"] = 6
        edited = validate_experiment_design(edited_data)
        options = _accepted_options(design, edited.spec.fingerprint)
        record = options["experiment_design"]
        self.assertEqual(record["application_status"], "edited_after_proposal")
        self.assertNotEqual(
            record["proposal"]["proposed_specification_fingerprint"],
            record["applied_specification_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
