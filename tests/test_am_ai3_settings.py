"""AI settings remain opt-in and contain no remote credentials."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ac.ai import AIAssistantSettings, load_ai_settings, save_ai_settings
from ac.gui.ai_assistant import build_candidate_evidence


class AMAI3SettingsTests(unittest.TestCase):
    def test_missing_settings_are_disabled_without_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = load_ai_settings(Path(directory) / "absent.json")
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.model, "")
        self.assertEqual(settings.endpoint, "http://localhost:11434")

    def test_save_and_load_round_trip_only_local_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "ai.json"
            expected = AIAssistantSettings(enabled=True, model="qwen3.5:9b", timeout_seconds=240)
            save_ai_settings(expected, path)
            actual = load_ai_settings(path)
            document = json.loads(path.read_text(encoding="utf-8"))
            permissions = stat.S_IMODE(path.stat().st_mode)
        self.assertEqual(actual, expected)
        self.assertNotIn("api_key", document)
        self.assertNotIn("token", document)
        self.assertEqual(document["endpoint"], "http://localhost:11434")
        if os.name == "posix":
            self.assertEqual(permissions, 0o600)

    def test_invalid_version_or_nonlocal_endpoint_fails_clearly(self):
        with self.assertRaises(ValueError):
            AIAssistantSettings(enabled=True, endpoint="http://example.com:11434", model="m")
        with self.assertRaises(ValueError):
            AIAssistantSettings(enabled=True, model="")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ai.json"
            path.write_text('{"format":"wrong","version":0}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "open the local AI settings"):
                load_ai_settings(path)

    def test_candidate_context_is_bounded_and_keeps_failure_witnesses(self):
        class Question:
            def canonical_json(self):
                return json.dumps({"format": "test", "scenarios": [{"i": i} for i in range(4)]})

        job = SimpleNamespace(question=Question())
        row = {
            "program": "Identity()",
            "cost": 0,
            "matching_scenario_count": 1,
            "scenario_count": 4,
            "bijection_on_every_scenario": False,
            "scenario_results": [
                {"scenario_index": 0, "finite_match": True, "verified_through": 3},
                {"scenario_index": 1, "finite_match": False, "verified_through": 2,
                 "evaluation": {"first_failure": {"kind": "collision", "base_degree": 2, "detail": "witness"}}},
                {"scenario_index": 2, "finite_match": False, "verified_through": 1},
            ],
            "example_map_preview": {"base_degree": 2, "source": {"values": [1]}, "output": {"values": [1]}},
        }
        evidence = build_candidate_evidence(job, row, scenario_limit=2)
        self.assertEqual(evidence["research_question"]["omitted_scenario_count"], 2)
        self.assertEqual(len(evidence["candidate"]["scenario_results"]), 2)
        self.assertEqual(evidence["candidate"]["scenario_results"][1]["first_failure"]["kind"], "collision")
        self.assertEqual(evidence["evidence_status"], "finite computation; not a proof")


if __name__ == "__main__":
    unittest.main()
