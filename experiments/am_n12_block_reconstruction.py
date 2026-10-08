"""Reconstruct a known +2 map from a seeded block-recipe vocabulary.

This is explicitly not a blind rediscovery benchmark: the 108-recipe catalogue
contains increasing runs, reverse complement, and a two-maximum extension,
which are ingredients of the known map. The named map itself is withheld from
candidate generation. Independent enumeration is run separately.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.algebra.block_schemas import enumerate_block_schemas
from ac.discovery.synthesis import synthesize_bijections
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.generate.universes import modified_via_hat, revised_sequences
from ac.logic.predicates import Avoid, Modified, Revised


SEARCH_FORMAT = "ascent-machine-am-n12-block-reconstruction"
SEARCH_VERSION = 1
TRAINING_THROUGH = 4


def run() -> dict:
    """Search modified 111-avoiders to revised 111-avoiders with shift +2."""
    started = time.perf_counter()
    source = Modified() & Avoid("111")
    target = Revised() & Avoid("111")
    recipes = enumerate_block_schemas(2)
    catalogue_fingerprint = sha256(
        json.dumps([repr(recipe) for recipe in recipes], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    source_counts = []
    target_counts = []
    source_objects = 0
    for degree in range(1, TRAINING_THROUGH + 1):
        source_level = tuple(word for word in modified_via_hat(degree) if source.holds(word))
        target_level = tuple(word for word in revised_sequences(degree + 2) if target.holds(word))
        source_counts.append(len(source_level))
        target_counts.append(len(target_level))
        source_objects += len(source_level)

    report = synthesize_bijections(
        source,
        target,
        universe=modified_via_hat,
        target_universe=revised_sequences,
        degree_shift=2,
        atoms=recipes,
        max_cost=4,
        through=TRAINING_THROUGH,
        keep=len(recipes),
    )
    benchmark_question = {
        "format": SEARCH_FORMAT,
        "version": SEARCH_VERSION,
        "source": ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}]).to_dict(),
        "target": ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}]).to_dict(),
        "degrees": DegreeWindow(1, TRAINING_THROUGH).to_dict(),
        "source_offset": 0,
        "target_offset": 2,
        "maximum_cost": 4,
        "candidate_catalogue_count": len(recipes),
        "candidate_catalogue_fingerprint": catalogue_fingerprint,
    }
    question_fingerprint = sha256(
        json.dumps(benchmark_question, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "format": SEARCH_FORMAT,
        "version": SEARCH_VERSION,
        "benchmark": "modified-111-avoiders-to-revised-111-avoiders",
        "classification": "reconstruction_from_seeded_operations",
        "classification_note": (
            "The named target map was not supplied, but its structural ingredients are present in the "
            "seeded block grammar. This is a reconstruction from seeded operations, not blind discovery."
        ),
        "benchmark_question": benchmark_question,
        "benchmark_fingerprint": question_fingerprint,
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "search_guidance": {
            "source_family": "modified",
            "source_rule": "avoid 111",
            "target_family": "revised",
            "target_rule": "avoid 111",
            "source_offset": 0,
            "target_offset": 2,
            "degree_window": [1, TRAINING_THROUGH],
            "seeded_candidate": None,
            "reference_map_provided": False,
            "seeded_operations": ["increasing_runs", "reverse_complement", "max_pair_around_first"],
            "grammar": "all generated block schemas with expected net length shift +2",
            "grammar_size": len(recipes),
            "maximum_cost": 4,
        },
        "source_counts": source_counts,
        "target_counts": target_counts,
        "count_vectors_match": source_counts == target_counts,
        "source_objects_per_candidate": source_objects,
        "candidates_tested": report.normalized_candidates,
        "finite_bijection_candidates": [
            {
                "program": repr(candidate.transform),
                "cost": candidate.cost,
                "verified_through": candidate.verified_through,
            }
            for candidate in report.exact
        ],
        "near_miss_count": sum(candidate.failure is not None for candidate in report.ranked),
        "proof_status": "not_proved",
        "held_out_degrees": [TRAINING_THROUGH + 1],
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the block reconstruction record to this JSON file")
    args = parser.parse_args(argv)
    result = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not result["count_vectors_match"] or not result["finite_bijection_candidates"]:
        raise SystemExit("AM-N12 block reconstruction did not find a finite map candidate")


if __name__ == "__main__":
    main()
