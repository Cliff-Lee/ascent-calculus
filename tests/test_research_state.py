import os
import tempfile
import unittest
from unittest.mock import patch

from ac.gui.experiments import parse_experiment
from ac.gui.research_state import read_state, write_state


class ResearchStateTests(unittest.TestCase):
    def test_draft_and_saved_specification_survive_reload(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ASCENT_ENGINE_DATA_DIR": directory}):
            state = {
                "draft": {"experiment-stop": "7", "experiment-left-patterns": "2122"},
                "saved": [{"id": "test-1", "specification": {"question": "compare"}}],
            }
            self.assertEqual(write_state(state), state)
            self.assertEqual(read_state(), state)

    def test_rejects_saved_tests_without_a_specification(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ASCENT_ENGINE_DATA_DIR": directory}):
            with self.assertRaisesRegex(ValueError, "experiment specification"):
                write_state({"draft": {}, "saved": [{"id": "test-1"}]})

    def test_saved_engine_specification_can_be_parsed_and_rerun(self):
        spec = {
            "question": "compare", "start": 1, "stop": 4, "statistic": "none", "condition": None,
            "left": {"family": "modified", "degree_offset": 0, "rules": [{"mode": "avoid", "pattern": [2, 1, 2, 2]}]},
            "right": {"family": "modified", "degree_offset": 0, "rules": [{"mode": "avoid", "pattern": [2, 2, 1, 2]}]},
        }
        parsed = parse_experiment(spec)
        self.assertEqual(parsed.left.rules[0].pattern.values, (2, 1, 2, 2))
        self.assertEqual(parsed.right.rules[0].pattern.values, (2, 2, 1, 2))


if __name__ == "__main__":
    unittest.main()
