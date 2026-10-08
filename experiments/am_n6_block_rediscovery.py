"""Reproducible N6 block-schema reconstruction benchmark.

This checks that the expanded block grammar can reconstruct the existing
modified-111 to revised-111 degree-+2 map. Its status is deliberately labeled
as reconstruction from seeded operations, not independent discovery.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.algebra.block_schemas import BlockSchemaT
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import (
    TransformationGrammarSpec,
    TransformationSearchSpec,
    run_transformation_search,
)


class _BenchmarkContext:
    def checkpoint(self, state, progress):
        pass

    def check_control(self):
        pass


def run() -> dict:
    grammar = TransformationGrammarSpec(
        operations=("block_schemas",), selectors=(), boolean_selector_algebra=False,
        max_selectors=10, max_atoms=10_000, max_cost=3, max_steps=1,
        candidate_budget=10_000, expansion_budget=10_000, evaluation_budget=1_000_000,
    )
    source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
    target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
    spec = TransformationSearchSpec(
        source, target, DegreeWindow(1, 4), grammar,
        source_offset=0, target_offset=2,
    )
    job = type("Job", (), {"question": spec, "checkpoint": {}})()
    result = run_transformation_search(job, _BenchmarkContext())

    # Reveal the known recipe only after the search has finished. It is used
    # solely to classify the benchmark outcome and was not a synthesis seed.
    known = BlockSchemaT(
        "increasing_runs", "first_prior_block", "safe_up", "reverse_complement",
        "max_pair_around_first",
    )
    exact_programs = {row["program"] for row in result["exact_candidates"]}
    return {
        "benchmark": "modified-111-to-revised-111-at-degree-plus-2",
        "classification": "reconstructed_from_seeded_operations",
        "specification_fingerprint": spec.fingerprint,
        "grammar_version": spec.grammar_version,
        "base_degrees": [spec.degrees.start, spec.degrees.stop],
        "degree_shift": spec.degree_shift,
        "generated_block_schemas": result["generated_atom_count"],
        "candidates_tested": result["candidates_tested"],
        "candidate_space_exhausted": result["candidate_space_exhausted"],
        "exact_candidate_count": result["exact_candidate_count"],
        "known_recipe_reconstructed": repr(known) in exact_programs,
        "known_recipe": repr(known),
        "proof_status": "not_proved",
        "verified_through_base_degree": spec.degrees.stop,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
