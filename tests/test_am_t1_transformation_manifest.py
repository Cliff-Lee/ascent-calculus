"""AM-T1: transformation grammar scope is explicit in search provenance."""

import unittest

from ac.discovery.transformation_search import (
    GRAMMAR_VERSION,
    OPERATION_IDS,
    SELECTOR_IDS,
    TransformationGrammarSpec,
    transformation_grammar_manifest,
)
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_family import TransformationFamilySearchSpec, run_worker_search
from ac.discovery.transformation_search import TransformationSearchSpec


class AMT1TransformationManifestTests(unittest.TestCase):
    def test_manifest_names_every_registered_operation_and_selector(self):
        grammar = TransformationGrammarSpec(
            operations=("symmetry", "selector_sweeps"),
            selectors=("first", "asc_top"),
            position_bound=5,
            max_cost=3,
            max_steps=2,
        )
        manifest = transformation_grammar_manifest(grammar)
        self.assertEqual(manifest["grammar_version"], GRAMMAR_VERSION)
        self.assertEqual(tuple(row["id"] for row in manifest["operations"]), OPERATION_IDS)
        self.assertEqual(tuple(row["id"] for row in manifest["selectors"]), SELECTOR_IDS)
        self.assertEqual(
            tuple(row["id"] for row in manifest["operations"] if row["enabled"]),
            ("symmetry", "selector_sweeps"),
        )
        self.assertEqual(
            tuple(row["id"] for row in manifest["selectors"] if row["enabled"]),
            ("first", "asc_top"),
        )
        self.assertEqual(manifest["bounds"]["position_bound"], 5)
        self.assertEqual(manifest["bounds"]["max_cost"], 3)
        self.assertIn("not a complete map grammar", manifest["scope"])
        self.assertEqual(len(manifest["fingerprint"]), 64)

    def test_manifest_fingerprint_is_stable_and_changes_with_grammar_scope(self):
        original = TransformationGrammarSpec(operations=("symmetry",), selectors=())
        same = TransformationGrammarSpec(operations=("symmetry",), selectors=())
        broader = TransformationGrammarSpec(operations=("symmetry", "canonicalize"), selectors=())
        first = transformation_grammar_manifest(original)
        self.assertEqual(first, transformation_grammar_manifest(same))
        self.assertNotEqual(first["fingerprint"], transformation_grammar_manifest(broader)["fingerprint"])

    def test_legacy_grammar_manifest_rejects_operations_it_did_not_have(self):
        grammar = TransformationGrammarSpec(operations=("block_schemas",), selectors=())
        with self.assertRaisesRegex(ValueError, "does not support block schemas"):
            transformation_grammar_manifest(grammar, grammar_version="ac-definition-grammar-v1")

    def test_family_search_result_carries_the_exact_grammar_manifest(self):
        grammar = TransformationGrammarSpec(
            operations=("symmetry",), selectors=(), max_cost=1, max_steps=1,
            candidate_budget=4, expansion_budget=100,
            enumeration_budget=100_000, class_object_budget=100_000,
            evaluation_budget=500_000,
        )
        unrestricted = ClassSpec("ordinary")
        scenarios = (
            TransformationSearchSpec(unrestricted, unrestricted, DegreeWindow(1, 2), grammar),
            TransformationSearchSpec(
                unrestricted, unrestricted, DegreeWindow(1, 2), grammar,
                target_offset=1,
            ),
        )
        spec = TransformationFamilySearchSpec(
            scenarios, candidate_budget=4, enumeration_budget=100_000,
            class_object_budget=100_000, evaluation_budget=500_000,
        )

        class Context:
            def checkpoint(self, state, progress=None):
                pass

            def check_control(self):
                pass

        job = type("Job", (), {"question": spec, "checkpoint": {}})()
        result = run_worker_search(job, Context())
        self.assertEqual(result["grammar_manifest"], transformation_grammar_manifest(grammar))


if __name__ == "__main__":
    unittest.main()
