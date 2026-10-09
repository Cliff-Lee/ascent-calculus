"""AM-T2: group programs with identical finite family behavior."""

import unittest

from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_family import TransformationFamilySearchSpec, run_worker_search
from ac.discovery.transformation_search import TransformationGrammarSpec, TransformationSearchSpec


class AMT2FiniteBehaviorTests(unittest.TestCase):
    def test_equivalent_exact_programs_share_a_finite_family_fingerprint(self):
        grammar = TransformationGrammarSpec(
            operations=("symmetry", "canonicalize"), selectors=(),
            max_cost=3, max_steps=2, candidate_budget=150, expansion_budget=5_000,
            enumeration_budget=100_000, class_object_budget=100_000,
            evaluation_budget=10_000_000,
        )
        ordinary = ClassSpec("ordinary")
        scenarios = (
            TransformationSearchSpec(ordinary, ordinary, DegreeWindow(1, 3), grammar),
            TransformationSearchSpec(
                ordinary, ordinary, DegreeWindow(1, 3), grammar,
                source_offset=1, target_offset=1,
            ),
        )
        spec = TransformationFamilySearchSpec(
            scenarios, candidate_budget=150, enumeration_budget=100_000,
            class_object_budget=100_000, evaluation_budget=10_000_000,
        )

        class Context:
            def checkpoint(self, state, progress=None):
                self.last_state = state

            def check_control(self):
                pass

        context = Context()
        job = type("Job", (), {"question": spec, "checkpoint": {}})()
        result = run_worker_search(job, context)

        self.assertEqual(spec.to_dict()["version"], 1)
        self.assertEqual(TransformationFamilySearchSpec.from_dict(spec.to_dict()), spec)
        version_two_spec = spec.to_dict()
        version_two_spec["version"] = 2
        self.assertEqual(TransformationFamilySearchSpec.from_dict(version_two_spec), spec)
        self.assertEqual(result["family_search_version"], 1)
        self.assertEqual(result["family_checkpoint_version"], 3)
        self.assertEqual(result["exact_candidate_count"], 3)
        self.assertEqual(result["finite_behavior_group_count"], 1)
        group, = result["finite_behavior_groups"]
        self.assertEqual(group["candidate_count"], 3)
        self.assertEqual(group["example_program"], "Identity()")
        self.assertTrue(all(
            candidate["finite_family_map_fingerprint"] == group["finite_family_map_fingerprint"]
            for candidate in result["exact_candidates"]
        ))
        self.assertEqual(
            group["scenario_maps"], result["exact_candidates"][0]["finite_family_scenario_maps"],
        )
        self.assertEqual(
            [item["scenario_fingerprint"] for item in group["scenario_maps"]],
            [scenario.fingerprint for scenario in scenarios],
        )
        self.assertEqual(result["proof_status"], "not_proved")
        self.assertIn("only over the listed finite", result["finite_behavior_scope"])

        resumed_job = type("Job", (), {
            "question": spec, "checkpoint": context.last_state,
        })()
        resumed = run_worker_search(resumed_job, Context())
        self.assertEqual(resumed["finite_behavior_groups"], result["finite_behavior_groups"])


if __name__ == "__main__":
    unittest.main()
