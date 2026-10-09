"""Blindly rediscover the ordinary-to-modified ascent-sequence sweep.

The search receives only the two class definitions and a generic selector-sweep
grammar. It does not enable the named hat-sweep operation or seed a target map.
The finite result is a bounded rediscovery, not a proof.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import (
    TransformationGrammarSpec,
    TransformationSearchSpec,
    run_transformation_search,
)


SEARCH_FORMAT = "ascent-machine-am-n12-blind-search"
SEARCH_VERSION = 1
TRAINING_THROUGH = 5


class _SearchContext:
    def checkpoint(self, state, progress):
        pass

    def check_control(self):
        pass


def run() -> dict:
    """Search generic raw-ascent-top sweeps for A_n -> M_n."""
    grammar = TransformationGrammarSpec(
        operations=("selector_sweeps",),
        selectors=("raw_asc_top",),
        boolean_selector_algebra=False,
        occurrence_rank=1,
        max_selectors=16,
        max_atoms=32,
        max_cost=2,
        max_steps=1,
        candidate_budget=32,
        expansion_budget=128,
        class_object_budget=20_000,
        enumeration_budget=20_000,
        evaluation_budget=100_000,
    )
    spec = TransformationSearchSpec(
        ClassSpec.build("ordinary"),
        ClassSpec.build("modified"),
        DegreeWindow(1, TRAINING_THROUGH),
        grammar,
    )
    result = run_transformation_search(
        type("Job", (), {"question": spec, "checkpoint": {}})(),
        _SearchContext(),
    )
    question = spec.to_dict()
    question_fingerprint = sha256(
        json.dumps(question, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "format": SEARCH_FORMAT,
        "version": SEARCH_VERSION,
        "benchmark": "ordinary-to-modified-ascent-sequences",
        "classification": "blind_bounded_rediscovery",
        "classification_note": (
            "The target map was withheld. The search generated candidates from a generic "
            "definition-derived selector-sweep grammar; the selected recipe is finite evidence."
        ),
        "benchmark_question": question,
        "benchmark_fingerprint": question_fingerprint,
        "spec_fingerprint": spec.fingerprint,
        "search_guidance": {
            "source_family": "ordinary",
            "target_family": "modified",
            "source_offset": 0,
            "target_offset": 0,
            "degree_window": [1, TRAINING_THROUGH],
            "seeded_candidate": None,
            "target_map_provided": False,
            "target_map_atom_enabled": False,
            "operations": list(grammar.operations),
            "selectors": list(grammar.selectors),
            "grammar": "generic snapshot-selected prefix-lift sweeps over generated position selectors",
            "candidate_budget": grammar.candidate_budget,
            "maximum_cost": grammar.max_cost,
            "maximum_steps": grammar.max_steps,
        },
        "generated_atom_count": result["generated_atom_count"],
        "candidates_tested": result["candidates_tested"],
        "candidate_space_exhausted": result["candidate_space_exhausted"],
        "exact_candidate_count": result["exact_candidate_count"],
        "finite_bijection_candidates": result["exact_candidates"],
        "near_misses": result["near_misses"],
        "proof_status": "not_proved",
        "held_out_degrees": [6, 7],
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the blinded search record to this JSON file")
    args = parser.parse_args(argv)
    result = run()
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if result["exact_candidate_count"] < 1 or not result["candidate_space_exhausted"]:
        raise SystemExit("AM-N12 blind search did not exhaust its candidate budget with a finite match")


if __name__ == "__main__":
    main()
